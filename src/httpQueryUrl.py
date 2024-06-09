import logging
import json  # for debug only, can be removed when all work fine...
import httpx

logger = logging.getLogger(name=__name__)

async def queryUrl(
    url, method="get", data=None, debug=False, timeout=1
) -> None | httpx.Response:
    methods = ["get", "post", "put", "delete"]
    if method in methods:
        try:
            response = httpx.request(method=method, url=url, data=data, timeout=timeout)
            if response.status_code != 200:
                logger.info(
                    msg=f"Error {response.status_code} something went wrong, request error."
                )
            else:
                logger.debug(msg="OK, request done.")
                if debug:
                    logger.info(
                        msg=f"\nRequest method: {method}\nType of data: "
                        f"{type(data)}\nData: {json.dumps(obj=data, indent=4)}\nServer response:\n{response.text}"
                    )
                return response
        except httpx.RequestError as e:
            logger.critical(
                msg=f"Error something went wrong, request-->connection error: \n{e}"
            )
    else:
        logger.error(msg=f"Invalid method: {method}")
    return None


if __name__ == "__main__":
    raise SystemExit
