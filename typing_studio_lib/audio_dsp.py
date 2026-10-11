"""Digital Signal Processing (DSP) Engine and Loudness Utilities."""
from __future__ import annotations
from typing import Optional
import math, numpy as np

try:
    from scipy.signal import lfilter as _scipy_lfilter, fftconvolve as _scipy_fftconvolve
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

try:
    import numba
    from numba import njit
    _HAS_NUMBA = True
except ImportError:
    _HAS_NUMBA = False

if _HAS_NUMBA:
    @njit(cache=True)
    def _nb_k_weight(x, sr):
        n = len(x); y = np.empty(n, dtype=np.float64)
        if sr == 48000:
            s1_b0, s1_b1, s1_b2 = 1.53512485958624, -2.61187896900947, 1.23925952524423
            s1_a1, s1_a2 = -1.69019851598276, 0.732626261909496
            s2_b0, s2_b1, s2_b2 = 1.0, -2.0, 1.0
            s2_a1, s2_a2 = -1.99004745481143, 0.990072500365666
        elif sr == 44100:
            s1_b0, s1_b1, s1_b2 = 1.53058976, -2.60968407, 1.24087861
            s1_a1, s1_a2 = -1.68589681, 0.73233165
            s2_b0, s2_b1, s2_b2 = 1.0, -2.0, 1.0
            s2_a1, s2_a2 = -1.98993544, 0.98996959
        else:
            for i in range(n): y[i] = x[i]
            return y
        z1 = z2 = 0.0
        for i in range(n):
            xn = x[i]; yn = s1_b0*xn + z1
            z1 = s1_b1*xn - s1_a1*yn + z2
            z2 = s1_b2*xn - s1_a2*yn
            y[i] = yn
        z1 = z2 = 0.0
        for i in range(n):
            xn = y[i]; yn = s2_b0*xn + z1
            z1 = s2_b1*xn - s2_a1*yn + z2
            z2 = s2_b2*xn - s2_a2*yn
            y[i] = yn
        return y

    @njit(cache=True)
    def _nb_compute_loudness(x_k):
        n = len(x_k)
        if n == 0: return -70.0
        s = 0.0
        for i in range(n):
            v = x_k[i]; s += v*v
        ms = s / n
        if ms < 1e-20: return -70.0
        return -0.691 + 10.0 * np.log10(ms)

    @njit(cache=True)
    def _nb_apply_gain(x, gain):
        n = len(x); out = np.empty(n, dtype=np.float64)
        for i in range(n): out[i] = x[i] * gain
        return out

    @njit(cache=True)
    def _nb_master_limiter(x, threshold):
        n = len(x); out = np.empty(n, dtype=np.float64)
        gain = 1.0; rs = 1.0 / 2400.0
        for i in range(n):
            xn = x[i]; ax = xn
            if ax < 0.0: ax = -ax
            if ax * gain > threshold:
                tg = threshold / max(ax, 1e-10)
                gain = gain * 0.9 + tg * 0.1
            else:
                gain = min(1.0, gain + rs)
            out[i] = xn * gain
        return out

    @njit(cache=True)
    def _nb_env_follower(env, attack_coeff, release_coeff):
        n = len(env)
        out = np.empty(n, dtype=np.float32)
        current = 0.0
        for i in range(n):
            if env[i] > current:
                current = current * attack_coeff + env[i] * (1.0 - attack_coeff)
            else:
                current = current * release_coeff + env[i] * (1.0 - release_coeff)
            out[i] = current
        return out

    @njit(cache=True)
    def _nb_apply_gain_comp(x, smooth_env, target_lin, ratio):
        n = len(x)
        out = np.empty(n, dtype=np.float32)
        for i in range(n):
            if smooth_env[i] > target_lin:
                g = 1.0 - (1.0 - 1.0 / ratio) * (1.0 - target_lin / smooth_env[i])
            else:
                g = 1.0
            out[i] = x[i] * g
        return out

    @njit(cache=True)
    def _nb_lookahead_gain(smooth_env, target_lin):
        n = len(smooth_env)
        gain = np.ones(n, dtype=np.float32)
        for i in range(n):
            if smooth_env[i] > target_lin:
                gain[i] = target_lin / smooth_env[i]
        return gain

    @njit(cache=True)
    def _nb_mix(mix, flat, offsets, lengths, starts):
        n_mix, n_flat = mix.shape[0], flat.shape[0]
        for i in range(len(starts)):
            s, ln, o = starts[i], lengths[i], offsets[i]
            for j in range(ln):
                if s + j < n_mix and o + j < n_flat:
                    mix[s + j] += flat[o + j]

class DSP:
    @staticmethod
    def env_exp(n: int, sr: int, attack: float = 0.001, decay_rate: float = 30.0, attack_curve: float = 2.0) -> np.ndarray:
        t = np.arange(n, dtype=np.float64) / sr
        env = np.exp(-t * decay_rate)
        a_samp = max(1, int(attack * sr))
        if a_samp < n:
            a_env = np.linspace(0, 1, a_samp, dtype=np.float64) ** attack_curve
            env[:a_samp] = a_env * np.exp(-np.arange(a_samp, dtype=np.float64) / sr * decay_rate)
        return env

    @staticmethod
    def fir_lowpass(cutoff: float, sr: int = 44100, n_taps: int = 127, window: str = "blackman") -> np.ndarray:
        if n_taps % 2 == 0: n_taps += 1
        cutoff = min(max(1.0, cutoff), sr / 2.0 - 1.0)
        if cutoff <= 0: return np.zeros(n_taps)
        fc = cutoff / sr; n = np.arange(n_taps, dtype=np.float64); center = (n_taps - 1) / 2.0
        h = np.sinc(2 * fc * (n - center))
        match window:
            case "blackman": w = 0.42 - 0.5*np.cos(2*np.pi*n/(n_taps-1)) + 0.08*np.cos(4*np.pi*n/(n_taps-1))
            case "hamming": w = 0.54 - 0.46*np.cos(2*np.pi*n/(n_taps-1))
            case "hann": w = 0.5 - 0.5*np.cos(2*np.pi*n/(n_taps-1))
            case _: w = np.ones(n_taps)
        h *= w; s = np.sum(h)
        if s > 0: h /= s
        return h

    @staticmethod
    def fir_highpass(cutoff: float, sr: int = 44100, n_taps: int = 127, window: str = "blackman") -> np.ndarray:
        hlp = DSP.fir_lowpass(cutoff, sr, n_taps, window); h = -hlp; h[len(h)//2] += 1.0; return h

    @staticmethod
    def fir_bandpass(low: float, high: float, sr: int = 44100, n_taps: int = 255, window: str = "blackman") -> np.ndarray:
        return DSP.fir_lowpass(high, sr, n_taps, window) - DSP.fir_lowpass(low, sr, n_taps, window)

    @staticmethod
    def convolve(x: np.ndarray, h: np.ndarray) -> np.ndarray:
        n, nh = len(x), len(h)
        if nh <= 1: return x * h[0] if nh == 1 else x
        if _HAS_SCIPY and nh > 64: return _scipy_fftconvolve(x, h, mode='full')[:n].astype(np.float32)
        if nh < 64 and n < 2048: return np.convolve(x, h, mode='full')[:n].astype(np.float32)
        MAX_FFT_BITS = 20
        total = n + nh - 1
        if total.bit_length() <= MAX_FFT_BITS:
            n_fft = 1 << total.bit_length()
            return np.fft.irfft(np.fft.rfft(x, n_fft) * np.fft.rfft(h, n_fft), n_fft)[:n].astype(np.float32)
        n_fft = 1 << MAX_FFT_BITS
        block = n_fft - nh + 1
        H = np.fft.rfft(h, n_fft)
        out = np.zeros(total, dtype=np.float32)
        for i in range(0, n, block):
            end = min(i + block, n)
            yb = np.fft.irfft(np.fft.rfft(x[i:end], n_fft) * H, n_fft)
            out[i:i + min(len(yb), total - i)] += yb[:min(len(yb), total - i)]
        return out[:n].astype(np.float32)

    @staticmethod
    def filt_lp(x, c, sr=44100, n_taps=127): return DSP.convolve(x, DSP.fir_lowpass(c, sr, n_taps))
    @staticmethod
    def filt_hp(x, c, sr=44100, n_taps=127): return DSP.convolve(x, DSP.fir_highpass(c, sr, n_taps))
    @staticmethod
    def filt_bp(x, l, h, sr=44100, n_taps=255): return DSP.convolve(x, DSP.fir_bandpass(l, h, sr, n_taps))

    @staticmethod
    def filt_resonator(x, f, q, sr=44100, gain=1.0):
        w0 = 2 * np.pi * f / sr
        r = np.exp(-w0 / (2 * max(0.5, q)))
        wd = w0 * np.sqrt(max(0.0, 1.0 - 1.0 / (4 * q * q))) if q > 0.5 else w0
        n_ir = min(len(x), max(16, int(sr * max(0.005, 6.0 * q / max(1.0, f)))))
        t = np.arange(n_ir, dtype=np.float64)
        ir = (r ** t) * np.sin(wd * t)
        p = np.max(np.abs(ir))
        if p > 1e-10: ir = ir / p * gain
        return DSP.convolve(x, ir)

    @staticmethod
    def sat_tube(x, drive=1.0):
        if drive <= 0: return x
        return (np.tanh(x * drive) / max(0.001, np.tanh(drive))).astype(np.float32)

    @staticmethod
    def sat_hard(x, t=1.0): return np.clip(x, -t, t).astype(np.float32)

    @staticmethod
    def sat_oversampled(x, drive=1.5):
        if drive <= 0: return x
        n = len(x)
        if n < 2: return DSP.sat_tube(x, drive)
        x_up = np.zeros(n * 2, dtype=np.float32)
        x_up[0::2] = x
        x_up[1:-1:2] = (x[:-1] + x[1:]) / 2.0
        x_up[-1] = x[-1]
        y_up = DSP.sat_tube(x_up, drive)
        y_down = (y_up[0:-1:2] + y_up[1::2]) / 2.0
        return y_down[:n].astype(np.float32)

    @staticmethod
    def binaural_pan(mono, pan, sr=44100):
        if abs(pan) < 0.01: return mono.copy(), mono.copy()
        if pan > 0:
            left = DSP.filt_hp(mono, 6000, sr, n_taps=127) * (1.0 - pan * 0.6)
            right = mono * min(1.0, 1.0 + pan * 0.2)
        else:
            right = DSP.filt_hp(mono, 6000, sr, n_taps=127) * (1.0 + pan * 0.6)
            left = mono * min(1.0, 1.0 - pan * 0.2)
        itd_samp = int(abs(pan) * 0.0006 * sr)
        l_out = np.zeros(len(mono) + itd_samp, dtype=np.float32)
        r_out = np.zeros(len(mono) + itd_samp, dtype=np.float32)
        if pan > 0:
            l_out[itd_samp:itd_samp + len(left)] += left
            r_out[:len(mono)] += right
        else:
            r_out[itd_samp:itd_samp + len(right)] += right
            l_out[:len(mono)] += left
        return l_out, r_out

    @staticmethod
    def compressor_rms(x, sr, threshold_db=-12.0, ratio=3.0, attack_ms=10, release_ms=100):
        if threshold_db >= 0 or ratio <= 1: return x.astype(np.float32)
        target_lin = 10 ** (threshold_db / 20)
        env = np.abs(x).astype(np.float32)
        ac = np.exp(-1.0 / (sr * (attack_ms / 1000.0)))
        rc = np.exp(-1.0 / (sr * (release_ms / 1000.0)))
        if _HAS_NUMBA:
            smooth_env = _nb_env_follower(env, ac, rc)
            return _nb_apply_gain_comp(x.astype(np.float32), smooth_env, target_lin, ratio)
        if _HAS_SCIPY:
            env_a = _scipy_lfilter([1 - ac], [1, -ac], env)
            env_r = _scipy_lfilter([1 - rc], [1, -rc], env)
            smooth_env = np.maximum(env_a, env_r).astype(np.float32)
        else:
            smooth_env = env
        gain = np.ones_like(x, dtype=np.float32)
        mask = smooth_env > target_lin
        gain[mask] = 1.0 - (1.0 - 1.0 / ratio) * (1.0 - target_lin / smooth_env[mask])
        return (x * gain).astype(np.float32)

    @staticmethod
    def lookahead_limiter(x, sr=44100, threshold_db=-1.0, release_ms=50):
        target_lin = 10 ** (threshold_db / 20)
        peak = np.max(np.abs(x))
        if peak <= target_lin: return x.astype(np.float32)
        ac = np.exp(-1.0 / (sr * 0.001))
        rc = np.exp(-1.0 / (sr * (release_ms / 1000.0)))
        env = np.abs(x).astype(np.float32)
        if _HAS_NUMBA:
            smooth_env = _nb_env_follower(env, ac, rc)
            gain = _nb_lookahead_gain(smooth_env, target_lin)
        else:
            gain = np.ones_like(x, dtype=np.float32)
            mask = env > target_lin
            gain[mask] = target_lin / env[mask]
        lookahead = int(sr * 0.002)
        if lookahead > 0 and len(gain) > lookahead:
            gain = np.roll(gain, -lookahead)
            gain[-lookahead:] = gain[-lookahead - 1]
        return (x * gain).astype(np.float32)

    @staticmethod
    def dc_block(x, sr=44100): return DSP.filt_hp(x, 20.0, sr, n_taps=63)

    @staticmethod
    def osc_sine(f, n, sr, phase=0.0): return np.sin(2 * np.pi * f * (np.arange(n, dtype=np.float64) / sr) + phase).astype(np.float32)

    @staticmethod
    def osc_sweep(f1, f2, n, sr):
        if n <= 0: return np.zeros(0, dtype=np.float32)
        if f1 <= 0: f1 = 1.0
        if f2 <= 0: f2 = 1.0
        t = np.arange(n, dtype=np.float64) / sr
        freq = f1 * (f2 / f1) ** (t / (n / sr))
        return np.sin(2 * np.pi * np.cumsum(freq) / sr).astype(np.float32)

    @staticmethod
    def osc_fm(c, mr, mi, n, sr, phase=0.0):
        t = np.arange(n, dtype=np.float64) / sr
        return np.sin(2 * np.pi * c * t + mi * np.sin(2 * np.pi * c * mr * t) + phase).astype(np.float32)

    @staticmethod
    def osc_fm_multi(c, mrs, mis, n, sr):
        t = np.arange(n, dtype=np.float64) / sr
        ph = 2 * np.pi * c * t
        for mr, mi in zip(mrs, mis): ph += mi * np.sin(2 * np.pi * c * mr * t)
        return np.sin(ph).astype(np.float32)

    @staticmethod
    def osc_saw(f, n, sr):
        t = np.arange(n, dtype=np.float64) / sr
        sig = np.zeros(n, dtype=np.float64)
        for h in range(1, 17):
            fh = f * h
            if fh >= sr * 0.45: break
            sig += np.sin(2 * np.pi * fh * t) / h
        return (sig * 0.5).astype(np.float32)

    @staticmethod
    def noise_white(n, rng): return rng.randn(n).astype(np.float32)

    @staticmethod
    def noise_pink(n, rng, sr=44100):
        bs = min(n, sr * 5)
        white = rng.randn(bs).astype(np.float32)
        fft = np.fft.rfft(white)
        freqs = np.fft.rfftfreq(bs, 1.0 / sr)
        if len(freqs) > 1:
            freqs[0] = max(freqs[1], 1.0)
            fft[1:] /= np.sqrt(np.abs(freqs[1:]))
            fft[0] = 0
        pink = np.fft.irfft(fft, n=bs).astype(np.float32)
        p = np.max(np.abs(pink))
        if p > 1e-6: pink /= p
        reps, rem = n // bs, n % bs
        out = np.tile(pink, reps) if reps > 0 else np.array([], dtype=np.float32)
        if rem > 0: out = np.concatenate([out, pink[:rem]])
        return out

    @staticmethod
    def noise_brown(n, rng):
        white = rng.randn(n).astype(np.float32)
        brown = np.cumsum(white) - np.mean(np.cumsum(white))
        p = np.max(np.abs(brown))
        if p > 0: brown = brown / p
        return (brown * 0.5).astype(np.float32)

    @staticmethod
    def modal(modes, n, sr, inharmonicity=0.0):
        t = np.arange(n, dtype=np.float64) / sr
        out = np.zeros(n, dtype=np.float64)
        f0 = modes[0][0] if modes else 440.0
        for freq, decay, amp in modes:
            af = freq
            if inharmonicity > 0:
                nh = freq / f0
                af = freq * np.sqrt(1 + inharmonicity * nh * nh)
            out += np.sin(2 * np.pi * af * t) * np.exp(-decay * t) * amp
        p = np.max(np.abs(out))
        if p > 1e-6: out /= p
        return out.astype(np.float32)

    @staticmethod
    def normalize(x, target_db=-1.0):
        p = np.max(np.abs(x)) if len(x) > 0 else 0.0
        if p < 1e-10: return x
        return x * (10 ** (target_db / 20) / p)

    @staticmethod
    def to_int16(x, target_db=-1.0):
        x = DSP.normalize(x, target_db)
        x = DSP.sat_hard(x, 1.0)
        np.nan_to_num(x, copy=False, nan=0.0, posinf=1.0, neginf=-1.0)
        return np.clip(x * 32767, -32768, 32767).astype(np.int16)

    @staticmethod
    def master_mono(x, sr=44100, target_db=-0.1):
        if len(x) == 0: return x
        x = DSP.dc_block(x, sr)
        x = DSP.filt_hp(x, 25.0, sr, n_taps=127)
        sub = DSP.filt_bp(x, 40, 120, sr, n_taps=255)
        sub = DSP.sat_tube(sub * 1.4, 1.3)
        x = x + sub * 0.25
        x = x + DSP.filt_lp(x, 150, sr, n_taps=127) * 0.12
        x = x - DSP.filt_bp(x, 250, 500, sr, n_taps=255) * 0.12
        x = x + DSP.filt_hp(x, 10000, sr, n_taps=63) * 0.20
        x = DSP.compressor_rms(x, sr, threshold_db=-22.0, ratio=1.8, attack_ms=30, release_ms=220)
        x = DSP.compressor_rms(x, sr, threshold_db=-12.0, ratio=2.5, attack_ms=8, release_ms=100)
        x = DSP.sat_oversampled(x, drive=1.3)
        return np.clip(DSP.lookahead_limiter(x, sr, threshold_db=target_db), -1.0, 1.0).astype(np.float32)

    @staticmethod
    def master_stereo_asmr(mix_l, mix_r, sr=44100, target_db=-1.0):
        if len(mix_l) == 0: return mix_l, mix_r
        mix_l = DSP.dc_block(mix_l, sr); mix_r = DSP.dc_block(mix_r, sr)
        mix_l = DSP.filt_hp(mix_l, 25.0, sr, n_taps=127); mix_r = DSP.filt_hp(mix_r, 25.0, sr, n_taps=127)
        
        sub_l = DSP.filt_bp(mix_l, 40, 120, sr, n_taps=255)
        sub_r = DSP.filt_bp(mix_r, 40, 120, sr, n_taps=255)
        sub_l = DSP.sat_tube(sub_l * 1.4, 1.3); sub_r = DSP.sat_tube(sub_r * 1.4, 1.3)
        mix_l = mix_l + sub_l * 0.25; mix_r = mix_r + sub_r * 0.25

        mid = (mix_l + mix_r) * 0.5
        side = (mix_l - mix_r) * 0.5
        mid = DSP.filt_lp(mid, 10000, sr, n_taps=127)
        side = side * 1.12
        mix_l = mid + side; mix_r = mid - side

        ess_l = DSP.filt_bp(mix_l, 5000, 8500, sr, n_taps=255)
        ess_r = DSP.filt_bp(mix_r, 5000, 8500, sr, n_taps=255)
        ess_env_l = np.abs(ess_l).astype(np.float32); ess_env_r = np.abs(ess_r).astype(np.float32)
        ess_thresh = 0.12
        ess_gain_l = np.where(ess_env_l > ess_thresh, ess_thresh / np.maximum(ess_env_l, 1e-10), 1.0).astype(np.float32)
        ess_gain_r = np.where(ess_env_r > ess_thresh, ess_thresh / np.maximum(ess_env_r, 1e-10), 1.0).astype(np.float32)
        if _HAS_SCIPY:
            ess_gain_l = _scipy_lfilter([1.0], [1.0, -0.99], ess_gain_l).astype(np.float32)
            ess_gain_r = _scipy_lfilter([1.0], [1.0, -0.99], ess_gain_r).astype(np.float32)
        mix_l = mix_l - ess_l * (1.0 - ess_gain_l) * 0.4
        mix_r = mix_r - ess_r * (1.0 - ess_gain_r) * 0.4

        mix_l = DSP.sat_tube(mix_l, drive=1.25); mix_r = DSP.sat_tube(mix_r, drive=1.25)

        mix_l = DSP.compressor_rms(mix_l, sr, threshold_db=-24.0, ratio=1.6, attack_ms=40, release_ms=250)
        mix_r = DSP.compressor_rms(mix_r, sr, threshold_db=-24.0, ratio=1.6, attack_ms=40, release_ms=250)
        mix_l = DSP.compressor_rms(mix_l, sr, threshold_db=-12.0, ratio=2.5, attack_ms=8, release_ms=100)
        mix_r = DSP.compressor_rms(mix_r, sr, threshold_db=-12.0, ratio=2.5, attack_ms=8, release_ms=100)

        air_l = DSP.filt_hp(mix_l, 11000, sr, n_taps=63)
        air_r = DSP.filt_hp(mix_r, 11000, sr, n_taps=63)
        air_l = DSP.sat_tube(air_l, 1.8) * 0.5
        air_r = DSP.sat_tube(air_r, 1.8) * 0.5
        mix_l = mix_l + air_l * 0.15; mix_r = mix_r + air_r * 0.15

        mix_l = DSP.lookahead_limiter(mix_l, sr, threshold_db=target_db, release_ms=80)
        mix_r = DSP.lookahead_limiter(mix_r, sr, threshold_db=target_db, release_ms=80)
        return (np.clip(mix_l, -1.0, 1.0).astype(np.float32), np.clip(mix_r, -1.0, 1.0).astype(np.float32))

def _k_weight_pure(x, sr):
    if sr == 48000:
        s1b=[1.53512485958624,-2.61187896900947,1.23925952524423]; s1a=[1.0,-1.69019851598276,0.732626261909496]
        s2b=[1.0,-2.0,1.0]; s2a=[1.0,-1.99004745481143,0.990072500365666]
    elif sr == 44100:
        s1b=[1.53058976,-2.60968407,1.24087861]; s1a=[1.0,-1.68589681,0.73233165]
        s2b=[1.0,-2.0,1.0]; s2a=[1.0,-1.98993544,0.98996959]
    else:
        return x.copy()
    if _HAS_SCIPY:
        from scipy.signal import lfilter
        y = lfilter(s1b, s1a, x); y = lfilter(s2b, s2a, y)
        return y
    y = np.zeros_like(x); z1 = z2 = 0.0; b0, b1, b2 = s1b; a1, a2 = s1a[1], s1a[2]
    for i in range(len(x)):
        xn = x[i]; yn = b0 * xn + z1; z1 = b1 * xn - a1 * yn + z2; z2 = b2 * xn - a2 * yn; y[i] = yn
    z1 = z2 = 0.0; b0, b1, b2 = s2b; a1, a2 = s2a[1], s2a[2]
    for i in range(len(y)):
        xn = y[i]; yn = b0 * xn + z1; z1 = b1 * xn - a1 * yn + z2; z2 = b2 * xn - a2 * yn; y[i] = yn
    return y

def _compute_lufs(x, sr):
    if len(x) < sr//2: return -70.0
    xf = x.astype(np.float64)
    if _HAS_NUMBA:
        xk = _nb_k_weight(xf, sr); return float(_nb_compute_loudness(xk))
    xk = _k_weight_pure(xf, sr); ms = np.mean(xk**2)
    if ms < 1e-20: return -70.0
    return -0.691 + 10.0 * np.log10(ms)

def _normalize_to_lufs(x, sr, target_lufs=-14.0, tp_db=-1.0):
    if len(x) < sr//2: return x
    xf = x.astype(np.float64)
    cl = _compute_lufs(xf, sr)
    if not np.isfinite(cl) or cl <= -70.0: return x
    gdb = target_lufs - cl; gl = 10.0 ** (gdb / 20.0)
    if _HAS_NUMBA: xn = _nb_apply_gain(xf, gl)
    else: xn = xf * gl
    tp = 10.0 ** (tp_db / 20.0)
    if _HAS_NUMBA: xn = _nb_master_limiter(xn, tp)
    else:
        p = np.max(np.abs(xn))
        if p > tp: xn = xn * (tp / p)
    return xn
