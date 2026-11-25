@echo off
cd /d D:\PythonProject\product-listing-generator
call ..\.venv\Scripts\activate
python -m src.main >> output\run.log 2>&1