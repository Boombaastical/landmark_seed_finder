# OpenCL Driver Requirements

Landmark Seed Finder uses your GPU via OpenCL for fast seed searching. OpenCL is included automatically with standard GPU drivers — most users will not need to do anything extra.

## Supported hardware

| GPU brand | Driver to install | Notes |
|-----------|------------------|-------|
| NVIDIA (GeForce / RTX / GTX) | [GeForce Game Ready Driver](https://www.nvidia.com/drivers) | Any recent driver includes OpenCL |
| AMD (Radeon RX / RX Vega) | [AMD Software: Adrenalin Edition](https://www.amd.com/en/support) | Any recent driver includes OpenCL |
| Intel (UHD / Iris / Arc) | [Intel Graphics Driver](https://www.intel.com/content/www/us/en/download-center/home.html) | Included with Windows Update or Intel's driver package |

## If you see an OpenCL error on launch

1. **Update your GPU drivers** using the links above — this fixes the problem in most cases.
2. If you have integrated Intel graphics and no dedicated GPU, install the **Intel OpenCL Runtime** separately:
   - Download: [Intel OpenCL Runtime for Windows](https://www.intel.com/content/www/us/en/developer/articles/tool/opencl-drivers.html)
   - Install and restart, then launch the app again.
3. If the error persists, open an issue on the GitHub repository and include the full error message shown.

## Notes

- The app automatically selects the first available OpenCL device (your GPU). If you have multiple GPUs, set the environment variable `PYOPENCL_CTX=1` (or `2`, etc.) before launching to select a different device.
- Integrated graphics (Intel/AMD APU) works but will be slower than a dedicated GPU.
