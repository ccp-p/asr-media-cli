import hmac
import hashlib
from typing import Dict

def sign(key: bytes, msg: str) -> bytes:
    """使用HMAC-SHA256生成签名"""
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def get_signature_key(secret_key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    """生成用于AWS签名的密钥"""
    k_date = sign(('AWS4' + secret_key).encode('utf-8'), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    k_signing = sign(k_service, 'aws4_request')
    return k_signing

def aws_signature(secret_key: str, request_parameters: str, headers: Dict[str, str],
                  method: str = "GET", payload: str = '', region: str = "cn", service: str = "vod") -> str:
    """生成AWS签名"""
    canonical_uri = '/'
    canonical_querystring = request_parameters
    canonical_headers = '\n'.join([f"{key}:{value}" for key, value in headers.items()]) + '\n'
    signed_headers = ';'.join(headers.keys())
    payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

    amzdate = headers["x-amz-date"]
    datestamp = amzdate.split('T')[0]

    algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = f"{datestamp}/{region}/{service}/aws4_request"
    string_to_sign = f"{algorithm}\n{amzdate}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

    signing_key = get_signature_key(secret_key, datestamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature
