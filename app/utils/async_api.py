import requests
import datetime
def async_api_call(streamName, customer_id,image_name,cameraId,model_name,imgcount):
    """
    Asynchronously sends data to the API.
    """
    try:
        image_name = image_name
        img_url= f"https://inferenceimage.blob.core.windows.net/inferenceimages/{image_name}"
        send_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            'cameraid': cameraId, 
            'sendtime': send_time, 
            'imgurl': img_url,
            'modelname': model_name, 
            'ImgCount': int(imgcount),
            'customerid': customer_id,
            'streamname':streamName
        }
        api_url="http://142.93.213.150:3000/api/post-analytics"

        response = requests.post(api_url, json=data)
        if response.status_code == 200:
            print("Data sent successfully!")
        else:
            print("Failed to send data! Response Code:", response.status_code)
    except Exception as e:
        print(f"Error sending data to API: {e}")