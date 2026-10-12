"""Validation for self-contained VRM uploads used by bridge voice calls."""

import io
import json
import struct

from PIL import Image

AVATAR_MAX_BYTES = 25 * 1024 * 1024


def validate_voice_avatar(data: bytes) -> None:
    try:
        _validate(data)
    except (
        KeyError,
        TypeError,
        IndexError,
        AttributeError,
        struct.error,
        UnicodeError,
        json.JSONDecodeError,
        Image.DecompressionBombError,
    ) as error:
        raise ValueError('Invalid VRM file.') from error


def _validate(data: bytes) -> None:
    if len(data) > AVATAR_MAX_BYTES:
        raise ValueError('Avatar must be at most 25 MiB.')
    magic, version, size, json_size, chunk = struct.unpack_from('<5I', data)
    if magic != 0x46546C67 or version != 2 or size != len(data) or chunk != 0x4E4F534A:
        raise ValueError('Upload a binary VRM file.')
    if json_size > 2 * 1024 * 1024 or 28 + json_size > len(data):
        raise ValueError('Invalid avatar container.')
    model = json.loads(data[20 : 20 + json_size])
    binary_size, binary_type = struct.unpack_from('<2I', data, 20 + json_size)
    start = 28 + json_size
    if binary_type != 0x004E4942 or start + binary_size != len(data):
        raise ValueError('Invalid avatar binary data.')
    extension = model.get('extensions', {})
    vrm = extension.get('VRMC_vrm') or extension.get('VRM') or {}
    bones = vrm.get('humanoid', {}).get('humanBones', {})
    if isinstance(bones, list):
        bones = {bone['bone']: bone for bone in bones}
    nodes = model.get('nodes', [])
    for name in ('hips', 'spine', 'head', 'leftUpperArm', 'rightUpperArm', 'leftLowerArm', 'rightLowerArm'):
        node = bones.get(name, {}).get('node')
        if not isinstance(node, int) or not 0 <= node < len(nodes):
            raise ValueError(f'Avatar is missing its {name} bone. Upload a rigged VRM file.')
    buffers = model.get('buffers', [])
    images = model.get('images', [])
    if len(buffers) != 1 or buffers[0].get('uri') or not 0 <= buffers[0]['byteLength'] <= binary_size:
        raise ValueError('Embed all buffers in the VRM file.')
    if len(nodes) > 512 or len(images) > 32 or sum(a.get('count', 0) for a in model.get('accessors', [])) > 5_000_000:
        raise ValueError('This avatar is too complex for a voice call. Use a lighter export.')
    _validate_textures(model, data, start, binary_size)


def _validate_textures(model: dict, data: bytes, start: int, binary_size: int) -> None:
    pixels = 0
    for image in model.get('images', []):
        if image.get('uri') or image.get('mimeType') not in ('image/png', 'image/jpeg', 'image/webp'):
            raise ValueError('Embed PNG, JPEG or WebP textures in the VRM file.')
        view = model['bufferViews'][image['bufferView']]
        offset, length = view.get('byteOffset', 0), view['byteLength']
        if view.get('buffer', 0) != 0 or offset < 0 or length <= 0 or offset + length > binary_size:
            raise ValueError('Invalid embedded avatar texture.')
        with Image.open(io.BytesIO(data[start + offset : start + offset + length])) as texture:
            pixels += texture.width * texture.height
            if max(texture.size) > 4096 or pixels > 32 * 1024 * 1024:
                raise ValueError('Avatar textures are too large. Export at 2048px or below.')
            texture.verify()


ANIMATION_MAX_BYTES = 10 * 1024 * 1024


def validate_voice_animation(data: bytes) -> None:
    """Bound the binary data before any browser loader processes an authored clip."""
    import math

    try:
        if len(data) > ANIMATION_MAX_BYTES:
            raise ValueError('Animation must be at most 10 MiB.')
        magic, version, size, json_size, chunk = struct.unpack_from('<5I', data)
        if (magic, version, size, chunk) != (0x46546C67, 2, len(data), 0x4E4F534A):
            raise ValueError('Upload a binary VRMA file.')
        if json_size > 2 * 1024 * 1024 or 28 + json_size > len(data):
            raise ValueError('Invalid animation container.')
        model = json.loads(data[20 : 20 + json_size])
        binary_size, binary_type = struct.unpack_from('<2I', data, 20 + json_size)
        start = 28 + json_size
        if binary_type != 0x004E4942 or start + binary_size != len(data):
            raise ValueError('Invalid animation binary data.')
        ext = model.get('extensions', {}).get('VRMC_vrm_animation', {})
        bones = ext.get('humanoid', {}).get('humanBones', {})
        nodes = model.get('nodes', [])
        # Match the VRMA loader's compatibility fallback for unversioned exports.
        if ext.get('specVersion') not in (None, '1.0') or not bones or not 0 < len(nodes) <= 512:
            raise ValueError('Use a VRMA 1.0 humanoid animation.')
        for bone in bones.values():
            if type(bone.get('node')) is not int or not 0 <= bone['node'] < len(nodes):
                raise ValueError('Invalid animation bone.')
        parents = set()
        visiting, visited = set(), set()

        def visit(index):
            if type(index) is not int or not 0 <= index < len(nodes) or index in visiting:
                raise ValueError('Invalid animation node hierarchy.')
            if index in visited:
                return
            visiting.add(index)
            node = nodes[index]
            for key, length in (('translation', 3), ('rotation', 4), ('scale', 3), ('matrix', 16)):
                if key in node and (
                    len(node[key]) != length
                    or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in node[key])
                ):
                    raise ValueError('Invalid animation transform.')
            for child in node.get('children', []):
                if child in parents:
                    raise ValueError('Animation nodes must have a single parent.')
                parents.add(child)
                visit(child)
            visiting.remove(index)
            visited.add(index)

        for index in range(len(nodes)):
            visit(index)
        for scene in model.get('scenes', []):
            if any(type(n) is not int or not 0 <= n < len(nodes) for n in scene.get('nodes', [])):
                raise ValueError('Invalid animation scene.')

        def at(items, index):
            if type(index) is not int or not 0 <= index < len(items):
                raise ValueError('Invalid animation reference.')
            return items[index]

        buffers = model.get('buffers', [])
        if len(buffers) != 1 or 'uri' in buffers[0] or not binary_size - 3 <= buffers[0]['byteLength'] <= binary_size:
            raise ValueError('Embed all animation data in the VRMA file.')
        if any(model.get(key) for key in ('images', 'textures', 'meshes', 'skins')):
            raise ValueError('Export animation only, without meshes or textures.')
        if set(model.get('extensionsRequired', [])) - {'VRMC_vrm_animation'}:
            raise ValueError('Unsupported animation extension.')
        views = model.get('bufferViews', [])
        for view in views:
            offset, length = view.get('byteOffset', 0), view['byteLength']
            if view.get('buffer', 0) != 0 or offset < 0 or length <= 0 or offset + length > binary_size:
                raise ValueError('Invalid animation buffer.')
        accessors = model.get('accessors', [])
        if sum(a.get('count', 0) for a in accessors) > 500_000:
            raise ValueError('Animation has too many keyframes.')
        values = []
        for accessor in accessors:
            count = accessor['count']
            components = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}.get(accessor['type'])
            if (
                accessor.get('sparse')
                or accessor['componentType'] != 5126
                or not components
                or not 0 < count <= 500_000
            ):
                raise ValueError('Use float animation keyframes without sparse accessors.')
            view = at(views, accessor['bufferView'])
            stride = view.get('byteStride', components * 4)
            offset = accessor.get('byteOffset', 0)
            if (
                stride < components * 4
                or stride % 4
                or offset < 0
                or offset + (count - 1) * stride + components * 4 > view['byteLength']
            ):
                raise ValueError('Invalid animation accessor.')
            rows = [
                struct.unpack_from(
                    '<' + 'f' * components, data, start + view.get('byteOffset', 0) + offset + i * stride
                )
                for i in range(count)
            ]
            if any(not math.isfinite(v) for row in rows for v in row):
                raise ValueError('Animation keyframes must be finite.')
            values.append(rows)
        animations = model.get('animations', [])
        if len(animations) != 1 or not animations[0].get('channels') or len(animations[0]['channels']) > 256:
            raise ValueError('Export exactly one animation per VRMA file.')
        animation = animations[0]
        duration = 0
        body_nodes = {bone['node'] for bone in bones.values()}
        body = False
        for channel in animation['channels']:
            target = channel['target']
            if not 0 <= target['node'] < len(nodes) or target['path'] not in ('rotation', 'translation'):
                raise ValueError('Unsupported animation channel.')
            body |= target['node'] in body_nodes
            sampler = at(animation['samplers'], channel['sampler'])
            times, outputs = at(values, sampler['input']), at(values, sampler['output'])
            if accessors[sampler['input']]['type'] != 'SCALAR' or any(
                t[0] < 0 or (i and t[0] <= times[i - 1][0]) for i, t in enumerate(times)
            ):
                raise ValueError('Invalid animation timing.')
            interpolation = sampler.get('interpolation', 'LINEAR')
            if interpolation not in ('LINEAR', 'STEP'):
                raise ValueError('Export baked animation with linear or stepped keyframes.')
            if len(outputs) != len(times) or len(outputs[0]) != (4 if target['path'] == 'rotation' else 3):
                raise ValueError('Invalid animation output.')
            duration = max(duration, times[-1][0])
        if not body or not 0 < duration <= 60:
            raise ValueError('Use a body animation between 0 and 60 seconds.')
    except (
        KeyError,
        TypeError,
        IndexError,
        AttributeError,
        struct.error,
        UnicodeError,
        json.JSONDecodeError,
        OverflowError,
        RecursionError,
    ) as error:
        raise ValueError('Invalid VRMA file.') from error
