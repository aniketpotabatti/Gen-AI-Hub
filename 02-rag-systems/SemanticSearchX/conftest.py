"""Global pytest configuration for SemanticSearchX.

Sets KMP_DUPLICATE_LIB_OK=TRUE to prevent dual-OpenMP runtime conflicts
between Windows FAISS (libomp140) and PyTorch (libiomp5md) when tests
exercise both dense FAISS indexing and Torch-backed embedding models.
"""
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
