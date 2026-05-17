import asyncio
import logging
import signal
import sys
import os
from typing import Optional, List, Dict, Any

import structlog

from .config import (
    GITLAB_WORKER_ENABLED,
    GITLAB_WORKER_LOG_LEVEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)
from .job_queue import job_queue
from .gitlab_fetcher import create_gitlab_fetcher
from .chunker import chunker
from .embedder import embedder
from .vector_store import vector_store

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
    wiki_only = connection.get('wiki_only', False)
    file_types_text = connection.get('file_types', '').strip()
    file_types = [
        ext.strip().lower() if ext.strip().startswith('.') else f'.{ext.strip().lower()}'
        for ext in file_types_text.split(',')
        if ext.strip()
    ] if file_types_text else None

    log.info(f'Processing sync job {job_id}')
    job_queue.set_job_status(job_id, 'connecting', 5, 'Connecting to GitLab...')

    gitlab = None
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
            project_progress = int((idx / total_projects) * 80) + 20
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
                    configured_branch, wiki_only, file_types, idx, total_projects
                )
            except Exception as e:
                log.error(f'Error syncing project {project_id}: {e}')
                continue

        job_queue.set_job_status(job_id, 'completed', 100, 'Sync completed successfully')
        log.info(f'Job {job_id} completed successfully')

    except Exception as e:
        error_str = str(e)
        if '401' in error_str or 'Unauthorized' in error_str:
            error_str = 'GitLab authentication failed. Your Personal Access Token may be invalid or expired.'
        elif '403' in error_str or 'Forbidden' in error_str:
            error_str = 'GitLab access forbidden. Your token may lack the required permissions (api scope).'
        log.error(f'Error processing job {job_id}: {e}')
        job_queue.set_job_status(job_id, 'failed', 0, error_str)
    finally:
        if gitlab:
            await gitlab.close()


async def sync_project(gitlab, project_id: str, job_id: str, exclude_patterns: list = None, include_wiki: bool = False, configured_branch: str = None, wiki_only: bool = False, file_types: list = None, project_idx: int = 0, total_projects: int = 1) -> None:
    log.info(f'Syncing project {project_id}')

    try:
        project = await gitlab.get_project(project_id)
        project_name = project.get('name', project_id)
        project_path = project.get('path_with_namespace', project_id)
        branch = configured_branch or project.get('default_branch', 'main')
        web_url = project.get('web_url', '')
    except Exception as e:
        log.error(f'Failed to fetch project info for {project_id}: {e}')
        project_name = project_id
        project_path = project_id
        branch = configured_branch or 'main'
        web_url = ''

    collection_name = f'gitlab_{project_path.replace("/", "_")}'
    log.info(f'Project {project_name} -> collection: {collection_name}')

    vector_store.delete_collection(collection_name)

    job_queue.update_progress(
        job_id,
        int((project_idx / total_projects) * 80) + 20,
        f'Fetching files from {project_name} ({branch})...',
        {'stage': 'fetching', 'project_name': project_name, 'project_id': project_id, 'branch': branch}
    )

    file_items = []
    if not wiki_only:
        try:
            tree = await gitlab.list_repository_tree(project_id, ref=branch, recursive=True)
            file_items = [item for item in tree if item['type'] == 'blob']
            
            if file_types:
                file_items = [
                    item for item in file_items
                    if any(item['path'].lower().endswith(ft) for ft in file_types)
                ]
            log.info(f'Found {len(file_items)} files in {project_name}')
        except Exception as e:
            log.error(f'Failed to list repository tree for {project_name}: {e}')
            return

    semaphore = asyncio.Semaphore(10)
    processed_count = 0
    error_count = 0
    
    async def process_file(item):
        nonlocal processed_count, error_count
        file_path = item['path']
        if is_binary_file(file_path) or is_excluded_path(file_path, exclude_patterns):
            return

        async with semaphore:
            try:
                content = await gitlab.get_file_content(project_id, file_path, ref=branch)
                if not content or not content.strip():
                    return

                chunks = chunker.chunk_code(content, file_path)
                if not chunks:
                    return

                texts = [c['text'] for c in chunks]
                embeddings = await embedder.embed(texts)

                vector_items = []
                for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                    vector_items.append({
                        'id': f'{project_id}_{file_path}_chunk_{i}',
                        'text': chunk['text'],
                        'vector': emb,
                        'metadata': {
                            'project_id': str(project_id),
                            'project_name': project_name,
                            'project_path': project_path,
                            'file_path': file_path,
                            'chunk_index': i,
                            'job_id': job_id,
                            'source': 'repository',
                            'web_url': f"{web_url}/-/blob/{branch}/{file_path}" if web_url else '',
                        },
                    })
                
                if vector_items:
                    vector_store.insert(collection_name, vector_items)
                processed_count += 1
                
                if processed_count % 10 == 0:
                    job_queue.update_progress(
                        job_id,
                        int((project_idx / total_projects) * 80) + 20,
                        f'Processing {project_name}: {processed_count}/{len(file_items)} files',
                        {'stage': 'processing', 'processed': processed_count, 'total': len(file_items)}
                    )
            except Exception as e:
                log.error(f'Error processing {file_path}: {e}')
                error_count += 1

    if file_items:
        await asyncio.gather(*(process_file(item) for item in file_items))

    if include_wiki or wiki_only:
        try:
            await sync_wiki(gitlab, project_id, job_id, collection_name, exclude_patterns, file_types, web_url)
        except Exception as e:
            log.warning(f'Error syncing wiki: {e}')

    log.info(f'Completed {project_name}: {processed_count} files, {error_count} errors')


async def sync_wiki(gitlab, project_id: str, job_id: str, collection_name: str, exclude_patterns: list = None, file_types: list = None, web_url: str = '') -> None:
    log.info(f'Syncing wiki for project {project_id}')
    try:
        wiki_tree = await gitlab.list_repository_tree(project_id, ref='wiki', recursive=True)
        wiki_items = [item for item in wiki_tree if item['type'] == 'blob']
        
        async def process_wiki_item(item):
            file_path = item['path']
            if is_excluded_path(file_path, exclude_patterns):
                return
            try:
                content = await gitlab.get_file_content(project_id, file_path, ref='wiki')
                chunks = chunker.chunk_code(content, file_path)
                if not chunks:
                    return
                
                embeddings = await embedder.embed([c['text'] for c in chunks])
                vector_items = [{
                    'id': f'{project_id}_wiki_{file_path}_chunk_{i}',
                    'text': chunk['text'],
                    'vector': emb,
                    'metadata': {
                        'project_id': str(project_id),
                        'file_path': file_path,
                        'chunk_index': i,
                        'job_id': job_id,
                        'source': 'wiki',
                        'web_url': f"{web_url}/-/wikis/{file_path.replace('.md', '')}" if web_url else '',
                    },
                } for i, (chunk, emb) in enumerate(zip(chunks, embeddings))]
                
                if vector_items:
                    vector_store.insert(collection_name, vector_items)
            except Exception as e:
                log.debug(f'Error processing wiki file {file_path}: {e}')

        if wiki_items:
            await asyncio.gather(*(process_wiki_item(item) for item in wiki_items))
    except Exception as e:
        log.debug(f'Wiki sync failed: {e}')


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
