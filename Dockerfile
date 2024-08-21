
# config for my local server
# FROM python:3.8
# ENV UserName_10Bis=user_name
# ENV Password_10Bis=password
# ENV MAIL=MAIL_SENDER
# ENV MAIL_PASSWORD=EMAIL_PASSWORD
# WORKDIR /app
# COPY requirements.txt ./
# COPY 10Bis_main.py ./
# COPY settings.py ./
# RUN pip install --no-cache-dir -r requirements.txt
# CMD [ "python", "10Bis_main.py"]

# For AWS Lambda
FROM public.ecr.aws/lambda/python:3.8
COPY requirements.txt ${LAMBDA_TASK_ROOT}
COPY tenBis_app.py ${LAMBDA_TASK_ROOT}
COPY main.py ${LAMBDA_TASK_ROOT}
copy settings.py ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt
CMD [ "main.lambda_handler" ]