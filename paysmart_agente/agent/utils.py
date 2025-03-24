from rest_framework.response import Response
from rest_framework import status

def standard_response(status_type, data=None, message="", http_status=None):
    if http_status is None:
        if status_type == "success":
            http_status = status.HTTP_200_OK
        elif status_type == "error":
            http_status = status.HTTP_400_BAD_REQUEST
        else:
            http_status = status.HTTP_200_OK

    return Response({
        "status": status_type,
        "data": data,
        "message": message
    }, status=http_status)
