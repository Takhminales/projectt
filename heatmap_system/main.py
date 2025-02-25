from server import run_server

def main():
    import os
    if not os.path.exists("cache_images"):
        os.makedirs("cache_images")
    print("Starting Heatmap System server...")
    run_server(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()
