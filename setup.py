from setuptools import setup
import imu_api

setup(
    name="imu-api",
    version=imu_api.__version__,
    packages=["imu_api"],
    include_package_data=True,
    description="Provides a python interface to KE EMu through KE IMu, and allows you to query and extract data",
    long_description="Documentation at https://github.com/ixc/python-imu-api",
    author="The Interaction Consortium",
    author_email="admins@interaction.net.au",
    url="https://github.com/ixc/python-imu-api",
)
