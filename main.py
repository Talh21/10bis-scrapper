from tenBis_app import *

def main():
    app = App(MAIL_SENDER, TO_MAIL)
    app.run_app()


def lambda_handler(event, context):
    main()

if __name__ == '__main__':
    main()
