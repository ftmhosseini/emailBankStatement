This program connects to a bank service, retrieves transaction data, and sends the processed results to AWS SQS. It also sends email notifications for all scenarios, including both successful operations and failures.

The application uses structured try–except blocks to handle errors gracefully and prevent unexpected interruptions during execution.

All configuration variables—such as the bank API URL, access token, email credentials, AWS access key, AWS secret key, and SQS queue URL—are securely stored in a .env file.

The project uses the boto3 package to interact with AWS services and the python-dotenv package to load environment variables. Both dependencies are listed in the requirements.txt file.
