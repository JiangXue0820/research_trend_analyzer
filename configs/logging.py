import logging
import os

def configure_logging(log_dir: str = "logs", log_file: str = "agent.log") -> None:
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)
    logging.basicConfig(
        level=logging.INFO,
        filename=log_path,
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
