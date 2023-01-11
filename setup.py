import setuptools

with open("README.md", 'r',encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="log_added_func",
    version="0.1.3",
    author="YCKAO",
    author_email="kao0983326221@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YCkao5888/log_added_func.git",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],

    # 依賴模塊
    install_requires=[
        "concurrent-log-handler",
        "psutil",
    ],

    # python版本
    python_requires=">=3",
)