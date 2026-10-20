FROM 121021644041.dkr.ecr.ap-southeast-1.amazonaws.com/sagemaker-scikit-learn:1.9-0-cpu-py3

RUN pip install --no-cache-dir xgboost==3.4.1