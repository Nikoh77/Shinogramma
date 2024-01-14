import requests
import json  # for debug only, can be removed when all work fine...


async def queryUrl(logger, context, chat_id, url, method="get", data=None, debug=False):
    methods = ["get", "post", "put", "delete"]
    if method in methods:
        http_method = getattr(requests, method)
        try:
            if method == ("get" or "delete"):
                response = http_method(url)
            else:
                response = http_method(url, json=data)
            if response.status_code != 200:
                logger.info(
                    f"Error {response.status_code} something went wrong, request error."
                )
                return False
            else:
                logger.info("OK, request done.")
                if debug:
                    logger.info(
                        f"\nRequest method: {method}\nType of data: "
                        f"{type(data)}\nData: {json.dumps(obj=data, indent=4)}\nServer response:\n{response.text}"
                    )
                return response
        except requests.exceptions.RequestException as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Error something went wrong, request error-->connection \u26A0\ufe0f",
            )
            logger.critical(
                f"Error something went wrong, request-->connection error: \n{e}"
            )
            return False
    else:
        print(f"Invalid method: {method}")
        return False


if __name__ == "__main__":
    raise SystemExit
