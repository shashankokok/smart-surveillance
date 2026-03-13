import torch

# Check if CUDA is available
if torch.cuda.is_available():
    print("CUDA is available. PyTorch can use the GPU.")
    print("Number of available GPUs:", torch.cuda.device_count())
    print("Current GPU name:", torch.cuda.get_device_name(0))

    # Create a tensor on the CPU and move it to the GPU
    cpu_tensor = torch.randn(2, 3)
    gpu_tensor = cpu_tensor.to(torch.device("cuda"))

    print("\nCPU tensor:\n", cpu_tensor)
    print("CPU tensor device:", cpu_tensor.device)
    print("\nGPU tensor:\n", gpu_tensor)
    print("GPU tensor device:", gpu_tensor.device)

    # Perform a simple operation on the GPU
    result_gpu = gpu_tensor * gpu_tensor
    print("\nResult of an operation on GPU:\n", result_gpu)

else:
    print("CUDA is not available. PyTorch is running on CPU.")
    device = torch.device("cpu")
