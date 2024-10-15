# your_package/init_auth.py
from lp_microservice.lp_service import perform_authentication

def main():
    # set log level to INFO
    perform_authentication()
    print("Authentication completed.")