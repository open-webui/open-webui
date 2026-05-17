import asyncio
import logging
import signal
import sys
import os
from typing import Optional

import structlog

from .config import GITLAB_WORKER_ENABLED, GITLAB_WORKER_LOG_LEVEL, CHUNK_SIZE, CHUNK_OVERLAP, LOCAL_STORAGE_ENABLED, VECTOR_DB_PROVIDER
from .job_queue import job_queue
from .gitlab_fetcher import create_gitlab_fetcher
from .chunker import chunker
from .embedder import embedder
from .vector_store import vector_store
from .local_storage import local_storage

logging.basicConfig(
    level=getattr(logging, GITLAB_WORKER_LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

log = logging.getLogger(__name__)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

SHUTDOWN_EVENT = asyncio.Event()


def signal_handler(signum, frame):
    log.info(f'Received signal {signum}, initiating shutdown...')
    SHUTDOWN_EVENT.set()


async def process_sync_job(job_data: dict) -> None:
    job_id = job_data.get('job_id', '')
    connection = job_data.get('connection', {})
    project_ids = job_data.get('project_ids', [])

    exclude_patterns_text = connection.get('exclude_patterns', '')
    exclude_patterns = [
        line.strip() for line in exclude_patterns_text.split('\n')
        if line.strip() and not line.strip().startswith('#')
    ]
    include_wiki = connection.get('include_wiki', False)
    configured_branch = connection.get('branch', '').strip() or None

    log.info(f'Processing sync job {job_id}')
    job_queue.set_job_status(job_id, 'connecting', 5, 'Connecting to GitLab...')

    try:
        gitlab = create_gitlab_fetcher(
            url=connection.get('url', ''),
            token=connection.get('token', ''),
        )

        job_queue.set_job_status(job_id, 'connecting', 10, 'Testing GitLab connection...')
        await gitlab.test_connection()
        log.info(f'Connected to GitLab: {connection.get("url")}')
        job_queue.set_job_status(job_id, 'fetching_projects', 15, 'Connected to GitLab')

        if not project_ids:
            owner = connection.get('owner', '').strip()
            repo = connection.get('repo', '').strip()

            if owner and repo:
                project_identifier = f'{owner}/{repo}'
                try:
                    project = await gitlab.get_project(project_identifier)
                    project_ids = [str(project.get('id', ''))]
                    log.info(f'Specific repo: {project_identifier} (ID: {project_ids[0]})')
                    job_queue.set_job_status(job_id, 'fetching_projects', 20, f'Found specific repo: {owner}/{repo}')
                except Exception as e:
                    log.error(f'Failed to get project {project_identifier}: {e}')
                    job_queue.set_job_status(job_id, 'failed', 0, f'Failed to find project: {str(e)}')
                    return
            else:
                projects = await gitlab.list_projects(per_page=100)
                project_ids = [str(p['id']) for p in projects]
                log.info(f'Found {len(project_ids)} projects to sync')
                job_queue.set_job_status(job_id, 'fetching_projects', 20, f'Found {len(project_ids)} projects')

        total_projects = len(project_ids)
        for idx, project_id in enumerate(project_ids):
            project_progress = int((idx / total_projects) * 80) + 20  # 20-100 range for project sync
            job_queue.set_job_status(
                job_id,
                'syncing',
                project_progress,
                f'Syncing project {idx + 1} of {total_projects}',
                {'current_project': project_id, 'project_index': idx, 'total_projects': total_projects}
            )

            try:
                await sync_project(
                    gitlab, project_id, job_id, exclude_patterns, include_wiki,
                    configured_branch, idx, total_projects
                )
            except Exception as e:
                log.error(f'Error syncing project {project_id}: {e}')
                continue

        job_queue.set_job_status(job_id, 'completed', 100, 'Sync completed successfully')
        log.info(f'Job {job_id} completed successfully')

    except Exception as e:
        error_str = str(e)
        if '401' in error_str or 'Unauthorized' in error_str:
            error_str = 'GitLab authentication failed. Your Personal Access Token may be invalid or expired. Generate a new token with api scope in GitLab settings.'
        elif '403' in error_str or 'Forbidden' in error_str:
            error_str = 'GitLab access forbidden. Your token may lack the required permissions (api scope).'
        log.error(f'Error processing job {job_id}: {e}')
        job_queue.set_job_status(job_id, 'failed', 0, error_str)


async def sync_project(gitlab, project_id: str, job_id: str, exclude_patterns: list = None, include_wiki: bool = False, configured_branch: str = None, project_idx: int = 0, total_projects: int = 1) -> None:
    log.info(f'Syncing project {project_id}')

    collection_name = f'gitlab_{project_id}'

    vector_store.delete_collection(collection_name)

    project_name = project_id
    project_path = project_id
    branch = configured_branch

    if not branch:
        try:
            project = await gitlab.get_project(project_id)
            project_name = project.get('name', project_id)
            project_path = project.get('path_with_namespace', project_id)
            branch = project.get('default_branch', 'main')
        except Exception:
            branch = 'main'

    log.info(f'Project {project_name}: using branch "{branch}"')

    job_queue.update_progress(
        job_id,
        int((project_idx / total_projects) * 80) + 20,
        f'Fetching files from {project_name} ({branch})...',
        {'stage': 'fetching', 'project_name': project_name, 'project_id': project_id, 'branch': branch}
    )

    try:
        tree = await gitlab.list_repository_tree(project_id, ref=branch, recursive=True)
    except Exception as e:
        log.error(f'Failed to list repository tree for {project_name} on branch "{branch}": {e}')
        job_queue.update_progress(
            job_id,
            int(((project_idx + 1) / total_projects) * 80) + 20,
            f'Failed to fetch files from {project_name}: {str(e)}',
            {'stage': 'error', 'project_name': project_name, 'error': str(e)}
        )
        return

    file_items = [item for item in tree if item['type'] == 'blob']
    all_file_paths = [item['path'] for item in file_items]
    log.info(f'Found {len(all_file_paths)} files in project {project_id}')

    job_queue.update_progress(
        job_id,
        int((project_idx / total_projects) * 80) + 20,
        f'Found {len(all_file_paths)} files to process',
        {
            'stage': 'listing',
            'project_name': project_name,
            'files': all_file_paths,
            'total_files': len(all_file_paths)
        }
    )

    log.info(f'Files to process in {project_name}:')
    for fp in all_file_paths:
        log.info(f'  {fp}')

    total_files = len(file_items)
    processed = 0
    skipped_binary = 0
    skipped_excluded = 0
    skipped_empty = 0
    error_count = 0

    for idx, item in enumerate(file_items):
        file_path = item['path']

        if is_binary_file(file_path):
            skipped_binary += 1
            continue

        try:
            content = await gitlab.get_file_content(project_id, file_path, ref=branch)

            if is_excluded_path(file_path, exclude_patterns):
                skipped_excluded += 1
                continue

            if not content or not content.strip():
                skipped_empty += 1
                continue

            local_storage.save_file(project_id, file_path, content)

            chunks = chunker.chunk_text(content, file_path)

            texts = [chunk['text'] for chunk in chunks]
            if not texts:
                continue

            # Update progress for embedding stage
            embedding_progress = int(((idx + 1) / total_files) * 50)  # 0-50% for embedding
            job_queue.update_progress(
                job_id,
                int((project_idx / total_projects) * 80) + 20 + embedding_progress // total_projects,
                f'Embedding {file_path} ({idx + 1}/{total_files})',
                {
                    'stage': 'embedding',
                    'file_path': file_path,
                    'file_index': idx + 1,
                    'total_files': total_files,
                    'chunks': len(chunks)
                }
            )

            embeddings = await embedder.embed(texts)

            items = [
                {
                    'id': f'{project_id}_{file_path}_chunk_{i}',
                    'text': chunk['text'],
                    'vector': emb,
                    'metadata': {
                        'project_id': project_id,
                        'project_name': project_name,
                        'project_path': project_path,
                        'file_path': file_path,
                        'chunk_index': i,
                        'job_id': job_id,
                        'source': 'repository',
                    },
                }
                for i, emb in enumerate(embeddings)
                if i < len(chunks)
            ]

            if items:
                vector_store.insert(collection_name, items)

            processed += 1

        except Exception as e:
            error_count += 1
            log.warning(f'Error processing file {file_path}: {e}')
            continue

    local_size = local_storage.get_project_size(project_id) if LOCAL_STORAGE_ENABLED else 0

    job_queue.update_progress(
        job_id,
        int(((project_idx + 1) / total_projects) * 80) + 20,
        f'Completed {project_name}: {processed} files processed ({local_size / 1024:.1f} KB stored locally, embedded into {VECTOR_DB_PROVIDER})',
        {
            'stage': 'completed',
            'project_name': project_name,
            'processed_files': all_file_paths,
            'processed': processed,
            'skipped_binary': skipped_binary,
            'skipped_excluded': skipped_excluded,
            'skipped_empty': skipped_empty,
            'errors': error_count,
            'local_storage': f'{local_size / 1024:.1f} KB' if LOCAL_STORAGE_ENABLED else 'disabled',
            'vector_db': VECTOR_DB_PROVIDER,
        }
    )

    if include_wiki:
        try:
            await sync_wiki(gitlab, project_id, job_id, collection_name, exclude_patterns)
        except Exception as e:
            log.debug(f'Error syncing wiki: {e}')

    log.info(f'Completed syncing project {project_id}: {processed} files processed, {error_count} errors')


async def sync_wiki(gitlab, project_id: str, job_id: str, collection_name: str, exclude_patterns: list = None) -> None:
    log.info(f'Syncing wiki for project {project_id}')
    job_queue.update_progress(job_id, 90, f'Syncing wiki for project {project_id}...', {'stage': 'wiki', 'project_id': project_id})

    try:
        wiki_tree = await gitlab.list_repository_tree(project_id, ref='wiki', recursive=True)
        wiki_items = [item for item in wiki_tree if item['type'] == 'blob' and item['path'].endswith('.md')]

        log.info(f'Found {len(wiki_items)} wiki files')

        for idx, item in enumerate(wiki_items):
            file_path = item['path']

            if is_excluded_path(file_path, exclude_patterns):
                continue

            try:
                content = await gitlab.get_file_content(project_id, file_path, ref='wiki')

                chunks = chunker.chunk_text(content, file_path)

                texts = [chunk['text'] for chunk in chunks]
                if not texts:
                    continue

                job_queue.update_progress(
                    job_id, 90,
                    f'Processing wiki: {file_path} ({idx + 1}/{len(wiki_items)})',
                    {'stage': 'wiki', 'file_path': file_path, 'file_index': idx + 1, 'total_files': len(wiki_items)}
                )

                embeddings = await embedder.embed(texts)

                items = [
                    {
                        'id': f'{project_id}_wiki_{file_path}_chunk_{i}',
                        'text': chunk['text'],
                        'vector': emb,
                        'metadata': {
                            'project_id': project_id,
                            'file_path': file_path,
                            'chunk_index': i,
                            'job_id': job_id,
                            'source': 'wiki',
                        },
                    }
                    for i, emb in enumerate(embeddings)
                    if i < len(chunks)
                ]

                if items:
                    vector_store.insert(collection_name, items)

            except Exception as e:
                log.debug(f'Error processing wiki file {file_path}: {e}')
                continue

        log.info(f'Completed syncing wiki for project {project_id}')

    except Exception as e:
        log.debug(f'Wiki sync failed for project {project_id}: {e}')


def is_binary_file(file_path: str) -> bool:
    binary_extensions = [
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.exe', '.dll', '.so', '.dylib',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv',
        '.ttf', '.otf', '.woff', '.woff2',
        '.pyc', '.class', '.o', '.obj',
    ]
    return any(file_path.lower().endswith(ext) for ext in binary_extensions)


def is_excluded_path(file_path: str, exclude_patterns: list = None) -> bool:
    default_patterns = [
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        'dist', 'build', '.cache', '.egg-info',
        '.DS_Store', 'Thumbs.db',
    ]

    patterns = exclude_patterns if exclude_patterns else default_patterns

    return any(pattern in file_path for pattern in patterns)


async def run_worker():
    log.info('GitLab Worker starting...')

    while not SHUTDOWN_EVENT.is_set():
        try:
            job_data = job_queue.dequeue(timeout=5)

            if job_data:
                await process_sync_job(job_data)

        except Exception as e:
            log.error(f'Error in worker loop: {e}')
            await asyncio.sleep(1)

    log.info('GitLab Worker shutting down...')


def main():
    if not GITLAB_WORKER_ENABLED:
        log.info('GitLab Worker is disabled')
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    log.info('Starting GitLab Worker...')
    asyncio.run(run_worker())


if __name__ == '__main__':
    main()