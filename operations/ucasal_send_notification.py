def send_notification(url: str, message: str):
    """
    Send a notification to the specified URL with the given message.
    
    Args:
        url (str): The URL to send the notification to.
        message (str): The message to send.
    """
    response = requests.post(
                    url,
                    json={"mensaje": message},
                    verify=False,
                )
    return response
    