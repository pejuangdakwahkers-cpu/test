FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua berkas proyek
COPY . /app/

# Berikan izin eksekusi pada entrypoint dan kumpulkan file statis
RUN chmod +x /app/entrypoint.sh && python manage.py collectstatic --noinput

# Buka port 7860 untuk Hugging Face Spaces
EXPOSE 7860

# Jalankan entrypoint script
CMD ["/app/entrypoint.sh"]
