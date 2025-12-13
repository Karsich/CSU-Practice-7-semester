import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA доступен: {torch.cuda.is_available()}")
print(f"Название GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Нет GPU'}")