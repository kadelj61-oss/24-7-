from pyngrok import ngrok

ngrok.set_auth_token("39UxUzwEH18Wa1O3QqP6ezsLB0M_49Mq83F6KqXJ6YQZrkpNc")  # Get from https://dashboard.ngrok.com/
public_url = ngrok.connect(8080)
print(f"Public URL: {public_url}")
input("Press Enter to stop...")
ngrok.kill()
