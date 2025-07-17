/* eslint-disable prettier/prettier */
import aws from 'aws-sdk';
import dotenv from 'dotenv';

dotenv.config();

const region = 'eu-north-1';
const bucketName = 'direct-upload-s3-khelan';

const s3 = new aws.S3({
  region,
  accessKeyId: process.env.ACCESS_KEY_ID,
  secretAccessKey: process.env.SECRET_ACCESS_KEY,
  signatureVersion: '4',
});

export { s3, bucketName };
