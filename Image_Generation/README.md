# Image Generator using Generative AI and AWS

This project demonstrates a serverless architecture to generate images using Stability AI's Stable Diffusion model hosted on AWS Bedrock. The system is designed to process text prompts via REST API calls (Postman) and return pre-signed URLs for accessing the generated images.

---

## Project Overview

### Workflow:
1. **Input**: Users send text prompts via Postman to the REST API exposed by API Gateway.
2. **Processing**: 
   - API Gateway triggers an AWS Lambda function.
   - Lambda sends the prompt and inference parameters to AWS Bedrock, which hosts Stability AI's Stable Diffusion model.
3. **Output**:
   - The generated image is stored in an S3 bucket.
   - Lambda generates a pre-signed URL for the stored image.
   - The pre-signed URL is returned via API Gateway, allowing users to securely access the image.

---

## Architecture Diagram

![Movie_Poster_design_GenAI](https://github.com/user-attachments/assets/8c70cf1d-12d7-4d9b-b1f5-5166ae966dfc)


---

## Tech Stack

- **Postman**: To invoke the REST API and test requests.
- **API Gateway**: For managing REST API endpoints.
- **AWS Lambda**: For serverless processing of prompts and generating pre-signed URLs.
- **AWS Bedrock**: Hosting Stability AI's Stable Diffusion model for image generation.
- **AWS S3**: For storing generated images as objects.
- **CloudWatch Logs**: For monitoring and debugging.

---

## How to Run the Project

### Prerequisites:
- AWS account with permissions for API Gateway, Lambda, Bedrock, S3, and CloudWatch.
- Postman installed for testing API requests.

### Steps:
1. Clone this repository:
git clone https://github.com/phanikolla/GenAI_Projects.git
cd Gen_AI_Projects/Image_generator
2. Deploy the architecture using AWS services (API Gateway, Lambda, Bedrock, S3).
3. Use Postman to send a `POST` request to the API Gateway endpoint with a text prompt in the body:
{
"prompt": "A futuristic cityscape at sunset"
}
4. Receive the pre-signed URL in the response and use it to access the generated image.

---

## Example Request and Response

### Sample Input (Postman):
{
"prompt": "A serene mountain landscape with a lake"
}

### Sample Response:
{
"image_url": "https://<your_bucket>.s3.amazonaws.com/<generated_image>?AWSAccessKeyId=<key>&Signature=<signature>&Expires=<timestamp>"
}

---

## Future Enhancements

- Add support for batch processing multiple prompts.
- Integrate additional generative AI models for diverse outputs.
- Implement authentication for secure API access.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Contact

Feel free to reach out if you have questions or suggestions!

- **LinkedIn**: [My LinkedIn Profile](https://www.linkedin.com/in/phanikumarkolla/)
- **GitHub**: [My GitHub Profile](https://github.com/phanikolla)
