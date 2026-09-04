from settings import load_settings

if __name__ == "__main__":
    cfg = load_settings()
    print("environment :", cfg.get("environment"))
    print("database_url:", cfg.get("database_url"))
    print("redis_url   :", cfg.get("redis_url"))
    print("log_level   :", cfg.get("log_level"))
