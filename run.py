from backend.services.face_recognition import start_camera

def main():
    print("==================================================")
    print(" SocialCue - Real-Time Facial Recognition Started ")
    print("==================================================")
    
    try:
        start_camera()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Shutting down...")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
