FROM python:3.10-slim
WORKDIR /code

# Copy requirements first to leverage Docker caching
COPY ./requirements.txt /code/requirements.txt

# Install dependencies and download SpaCy model
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt \
    && python -m spacy download en_core_web_sm

# Copy the rest of your application code
COPY . .

# NEW STEP: Run your fine-tuning script to generate the model folder on the cloud
# (Replace 'trainer.py' with the exact name of your fine-tuning script file)
RUN python trainer.py

EXPOSE 7860
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "120"]
