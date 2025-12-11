# 🎨 Serverless Image Generator (Bedrock + Stable Diffusion)

[![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-FF9900?logo=amazonaws&style=for-the-badge)](https://aws.amazon.com/lambda/)
[![API Gateway](https://img.shields.io/badge/API-Gateway-red?logo=amazonaws&style=for-the-badge)](https://aws.amazon.com/api-gateway/)
[![Stable Diffusion](https://img.shields.io/badge/Model-Stable%20Diffusion-blue?style=for-the-badge)](https://stability.ai/)

## 📖 Overview
This project implements a fully **Serverless GenAI Architecture**. Instead of running heavy GPU instances to host image models, this solution leverages **Amazon Bedrock** to generate images via API calls. It exposes a REST API that accepts text prompts and returns secure, pre-signed S3 URLs for the generated images.

### 🚀 Key Features
*   **Zero Infrastructure Management:** purely serverless (Lambda + API Gateway).
*   **Secure Delivery:** Images are stored in a private S3 bucket and accessed only via time-limited Pre-signed URLs.
*   **Scalable:** Handles concurrent requests automatically via AWS Lambda.

## 🏗️ Architecture
![Architecture](./PosterDesign.gif)

## ⚙️ How it Works
1.  User sends a POST request to API Gateway: `{"prompt": "A futuristic city"}`.
2.  Lambda triggers Bedrock (Stable Diffusion model).
3.  Bedrock returns base64 image data.
4.  Lambda decodes and saves the image to a private **S3 Bucket**.
5.  Lambda generates a **Pre-signed URL** (valid for 5 mins) and returns it to the user.

## 💻 Usage (Postman)

**Endpoint:** `POST https://<your-api-id>.execute-api.us-east-1.amazonaws.com/prod/generate`

**Body:**
```json
{
  "prompt": "A cyberpunk workspace with neon lights, 8k resolution"
}
```

**Response:**
```json
{
  "status": "success",
  "image_url": "https://my-bucket.s3.amazonaws.com/gen-123.jpg?AWSAccessKeyId=..."
}
```

## 🧠 Key Learnings & Patterns
*   **Handling Binary Data:** API Gateway has a 10MB payload limit. Passing base64 images directly through the API response is bad practice. The **"S3 Pre-signed URL" pattern** used here is the enterprise-standard way to deliver large assets securely and efficiently.
*   **Cold Starts:** I optimized the Lambda function by moving the `boto3` client initialization outside the handler to reuse connections across warm invocations.

---
*Maintained by Phani Kolla*


---
