"""BatchTechUI: live machine stats (CPU, memory, GPU, network) for the sidebar status panel.

New file, so upstream merges never conflict with it. Ported from the HUD's /hud-auth/stats.
Note: inside Docker, psutil reports the host's CPU/memory. GPU needs nvidia-smi (or amdgpu sysfs) inside the container.
"""

import asyncio
import os
import shutil
import time
from pathlib import Path

import psutil
from fastapi import APIRouter, Depends, Request

from open_webui.utils.auth import get_verified_user
from open_webui.utils.batchtech_version import BATCHTECH_VERSION

router = APIRouter()

psutil.cpu_percent(interval=None)  # prime the counter: the next call reports use since this one
_net = {'t': time.time(), 'c': psutil.net_io_counters(), 'rate': None}
_gpu = {'at': 0.0, 'value': None}
_SKIP_NIC = ('lo', 'docker', 'br-', 'veth', 'virbr')


def _net_rate():
    now = time.time()
    dt = now - _net['t']
    if dt < 0.5:
        return _net['rate']
    pernic = psutil.net_io_counters(pernic=True)
    prev = _net['c']
    rx = tx = 0
    for name, c in pernic.items():
        if name.startswith(_SKIP_NIC):
            continue
        p = prev.get(name) if isinstance(prev, dict) else None
        if p:
            rx += max(0, c.bytes_recv - p.bytes_recv)
            tx += max(0, c.bytes_sent - p.bytes_sent)
    _net.update(t=now, c=pernic, rate={'down': rx / dt, 'up': tx / dt})
    return _net['rate']


_net['c'] = psutil.net_io_counters(pernic=True)


def _read_num(path):
    try:
        return float(Path(path).read_text().strip())
    except Exception:
        return None


def _amd_gpu():
    drm = Path('/sys/class/drm')
    if not drm.exists():
        return None
    for card in sorted(drm.glob('card[0-9]*')):
        d = card / 'device'
        busy = _read_num(d / 'gpu_busy_percent')
        if busy is None:
            continue
        total = _read_num(d / 'mem_info_vram_total')
        used = _read_num(d / 'mem_info_vram_used')
        vram = {'used': used, 'total': total} if total and used is not None else None
        return {'name': 'AMD GPU', 'util': busy / 100, 'vram': vram}
    return None


async def _nvidia_gpu():
    if not shutil.which('nvidia-smi'):
        return None
    try:
        proc = await asyncio.create_subprocess_exec(
            'nvidia-smi',
            '--query-gpu=name,utilization.gpu,memory.used,memory.total',
            '--format=csv,noheader,nounits',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=1.5)
        name, util, used, total = [x.strip() for x in out.decode().split('\n')[0].split(',')]
        vram = {'used': float(used) * 1048576, 'total': float(total) * 1048576} if float(total) > 0 else None
        return {'name': name, 'util': float(util) / 100, 'vram': vram}
    except Exception:
        return None


async def _gpu_stats():
    if time.time() - _gpu['at'] < 2:
        return _gpu['value']
    value = (await _nvidia_gpu()) or _amd_gpu()
    _gpu.update(at=time.time(), value=value)
    return value


async def _loaded_models(request: Request, user):
    """Models Ollama currently holds in memory (what is 'running' on this machine), with their memory use."""
    try:
        from open_webui.routers.ollama import get_ollama_loaded_models

        res = await asyncio.wait_for(get_ollama_loaded_models(request, user=user), timeout=2)
        return [
            {
                'name': m.get('model') or m.get('name'),
                'size': m.get('size'),
                'size_vram': m.get('size_vram'),
                'expires_at': m.get('expires_at'),
            }
            for m in res.get('models', [])
        ]
    except Exception:
        return []


@router.get('/stats')
async def get_stats(request: Request, user=Depends(get_verified_user)):
    mem = psutil.virtual_memory()
    return {
        'models': await _loaded_models(request, user),
        'cpu': psutil.cpu_percent(interval=None) / 100,
        'cores': os.cpu_count(),
        'mem': {'used': mem.total - mem.available, 'total': mem.total},
        'gpu': await _gpu_stats(),
        'net': _net_rate(),
    }


@router.get('/version')
async def get_version(user=Depends(get_verified_user)):
    from open_webui.env import VERSION

    return {'batchtech': BATCHTECH_VERSION, 'open_webui': VERSION}
