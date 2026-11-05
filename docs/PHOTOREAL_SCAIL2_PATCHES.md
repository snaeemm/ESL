# SCAIL-2 on one shared-memory GPU: the patches

Part of [PHOTOREAL_PRESENTER.md](PHOTOREAL_PRESENTER.md).

Upstream SCAIL-2 (`zai-org/SCAIL-2`, Wan-14B based) assumes a large discrete GPU. These are the changes that let it render the full lesson on a single AMD Ryzen AI Max (Strix Halo, gfx1151) workstation with 64 GB of memory shared between CPU and GPU (GPU heap capped at about 31 GB), on a ROCm nightly build of PyTorch. All of them live in `wan/scail.py` and `generate.py` of the SCAIL-2 checkout.

| # | Change | Why |
|---|---|---|
| 1 | Transformer blocks streamed from RAM (`SCAIL_STREAM_BLOCKS`, default 16), the rest resident on the GPU | The bf16 14B model does not fit in the GPU heap alongside activations |
| 2 | VAE **decode** on the CPU in fp32, per segment | The VAE asks for about 18 GB in one go on the GPU |
| 3 | VAE **encode** of the pose and history frames on the CPU (`_encode_cpu`) | Encoding the history frames for a long sign (TEACHER) ran out of GPU memory (17.7 GB request) |
| 4 | T5 text encoder dropped after the prompt is encoded (`self.text_encoder.model = None; gc.collect()`) | About 11 GB of RAM held for the whole render but used once |
| 5 | Driving video and masks prepared 64 frames at a time, kept in fp16 on the CPU, and moved to the GPU one segment at a time | A 1,434-frame one-take driver loaded as fp32 on the device was OOM-killed |
| 6 | Resumable segment cache (`SCAIL_SEG_CACHE`): every finished 49-frame segment is saved, and a restarted run loads it instead of re-rendering | A one-take lesson is 36 segments and many hours; a crash should cost one segment, not the run |

## Patch 3: CPU encode (simplified)

```python
def _encode_cpu(self, videos):
    vae = self.vae
    vae.model.to("cpu")
    vae.scale = [t.cpu() if torch.is_tensor(t) else t for t in vae.scale]
    with torch.autocast("cpu", enabled=False):
        out = [vae.model.encode(v.cpu().float().unsqueeze(0), vae.scale).float().squeeze(0) for v in videos]
    vae.model.to(self.device)
    vae.scale = [t.to(self.device) if torch.is_tensor(t) else t for t in vae.scale]
    return [o.to(self.device) for o in out]
```

`pose_latent = self.vae.encode(...)` and `history_latent = self.vae.encode(...)` both call `self._encode_cpu(...)` instead.

## Patch 5: chunked driver loading (`generate.py`)

```python
def prep(v):
    v = v.permute(0, 3, 1, 2)  # t c h w
    return torch.cat([((resize_for_rectangle_crop(v[i:i + 64].float(), (target_h, target_w), reshape_mode="center")
                        - 127.5) / 127.5).half() for i in range(0, len(v), 64)])
pose_video = prep(load_video_for_pose_sample(pose_path))
driving_mask_video = prep(load_video_for_pose_sample(driving_mask_path))
```

In `scail.py` the two `.to(self.device)` calls on the whole videos are removed, and each segment slice is moved instead: `pose_video[seg_start:seg_end].to(self.device).float()`.

## Patch 6: segment cache (`scail.py`, inside the segment loop)

```python
_cache = os.environ.get("SCAIL_SEG_CACHE")
_cf = os.path.join(_cache, f"seg{seg_idx:03d}.pt") if _cache else None
if _cf and os.path.exists(_cf):
    videos = [torch.load(_cf).float().to(self.device)]
else:
    videos = sample_func(noise, arg_c, arg_null, history_latent)
    if _cf and self.rank == 0:
        os.makedirs(_cache, exist_ok=True)
        torch.save(videos[0].half().cpu(), _cf + ".tmp")
        os.replace(_cf + ".tmp", _cf)
```

The noise for each segment is still drawn from the seeded generator before the cache check, so a resumed run produces the same frames as an uninterrupted one.

## Environment

```bash
export PYTORCH_HIP_ALLOC_CONF=expandable_segments:True
export TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1   # flash / memory-efficient SDPA on gfx1151
```
