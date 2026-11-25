"""Audio helpers that are not tied to a particular TTS backend."""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from .audio import flatten_mono


def _resample_linear(samples: np.ndarray, factor: float) -> np.ndarray:
    """Speed change by resampling: cheap, but it also shifts the pitch."""
    source = flatten_mono(samples)
    if source.size == 0 or abs(factor - 1.0) < 1e-6:
        return source
    target_length = max(1, int(round(source.size / factor)))
    positions = np.linspace(0.0, source.size - 1, target_length, dtype=np.float64)
    return np.interp(positions, np.arange(source.size, dtype=np.float64), source).astype(np.float32)


def change_speed(
    samples: np.ndarray,
    sample_rate: int,
    factor: float,
    warn: Optional[Callable[[str], None]] = None,
) -> np.ndarray:
    """Change the speaking rate of ``samples`` by ``factor``.

    ``factor`` > 1 speaks faster.  torchaudio's time stretcher is used when it is
    available so the pitch is preserved (this is what the local stack does);
    otherwise we fall back to plain resampling and warn once, because that path
    shifts the pitch as well.
    """
    if factor is None:
        return flatten_mono(samples)
    factor = float(factor)
    if factor <= 0:
        raise ValueError(f"speech rate must be positive, got {factor}")
    if abs(factor - 1.0) < 1e-3:
        return flatten_mono(samples)

    try:
        import torch
        import torchaudio
    except ImportError:
        if warn is not None:
            warn(
                "torchaudio is not installed: --speech-rate falls back to "
                "resampling, which also shifts the pitch"
            )
        return _resample_linear(samples, factor)

    tensor = torch.from_numpy(np.ascontiguousarray(flatten_mono(samples), dtype=np.float32))
    stretched = torchaudio.functional.speed(
        tensor.unsqueeze(0), orig_freq=int(sample_rate), factor=factor
    )
    if isinstance(stretched, tuple):  # older torchaudio returned (waveform, length)
        stretched = stretched[0]
    return flatten_mono(stretched.squeeze(0).cpu().numpy())
