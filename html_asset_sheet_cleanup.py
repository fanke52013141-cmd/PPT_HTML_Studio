"""Opt-in removal of detached near-transparent noise, preserving strong pixels."""
from __future__ import annotations

import math
import numpy as np

VERSION = 'alpha-micro-noise/0.1.0'


def validate_cleanup(params):
    if not isinstance(params, dict) or set(params) != {'threshold', 'guard_radius', 'max_removed_fraction'}:
        raise ValueError('透明清理参数字段不符')
    if type(params['threshold']) is not int or not 1 <= params['threshold'] <= 4:
        raise ValueError('透明阈值须为1–4整数')
    if type(params['guard_radius']) is not int or not 2 <= params['guard_radius'] <= 8:
        raise ValueError('主体保护半径须为2–8整数')
    fraction = params['max_removed_fraction']
    if type(fraction) not in (int, float) or not math.isfinite(fraction) or not 0 <= fraction <= .05:
        raise ValueError('透明清理像素预算须为0–0.05')


def clean_alpha(rgba, params):
    validate_cleanup(params)
    alpha = rgba[:, :, 3]
    strong = alpha > params['threshold']
    if not strong.any():
        raise ValueError('未找到可保护主体，不能清理全弱透明图')
    radius = params['guard_radius']
    height, width = alpha.shape
    padded = np.pad(strong, radius)
    protected = np.zeros_like(strong)
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            protected |= padded[dy:dy + height, dx:dx + width]
    removed = (alpha > 0) & (alpha <= params['threshold']) & ~protected
    count = int(removed.sum())
    if count / alpha.size > params['max_removed_fraction']:
        raise ValueError('透明清理超过声明像素预算')
    output = rgba.copy()
    output[removed, 3] = 0
    return output, {'version': VERSION, 'parameters': dict(params),
                    'removed_pixels': count, 'removed_alpha_mass': int(alpha[removed].astype(np.uint64).sum())}
