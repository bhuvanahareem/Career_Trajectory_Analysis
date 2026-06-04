# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /code

# Copy the requirements file into the container
COPY ./requirements.txt /code/requirements.txt

# Install dependencies and download the SpaCy model
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt \
    && python -m spacy download en_core_web_sm

# Copy the rest of the application code into the container
COPY . .

# Expose port 7860 (Hugging Face Spaces requires port 7860)
EXPOSE 7860

# Start the Flask app using Gunicorn on port 7860
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "120"]
