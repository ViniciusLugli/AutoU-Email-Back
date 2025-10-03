# run.py
import os
from multiprocessing import Process
import uvicorn
from app.services.celery import celery  # importa seu celery configurado

def start_celery_worker():
    celery.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=1", 
        "--autoscale=2,1"
    ])

if __name__ == "__main__":
    p = Process(target=start_celery_worker)
    p.start()

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

    p.join()
