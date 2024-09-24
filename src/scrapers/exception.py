import sys


def get_error_message_detail(error, error_detail: sys):
    _, _, exc_tb = error_detail.exc_info()
    file_name = exc_tb.tb_frame.f_code.co_filename
    line_number = exc_tb.tb_lineno
    error_message = f"Error occurred in Python script: [{file_name}], Line number: [{line_number}], Error message: {str(error)}"

    return error_message


class CustomException(Exception):
    def __init__(self, error_message, error_detail: sys):
        super().__init__(error_message)
        self.error_message = get_error_message_detail(
            error_message, error_detail=error_detail
        )

    def __str__(self):
        return self.error_message
    

#testing exception
# if __name__=="__main__":
#     try:
#         a=1/0
#     except Exception as e:
#         logging.info('Div by zero')
#         raise CustomException(e,sys)
    