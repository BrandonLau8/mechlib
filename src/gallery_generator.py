import boto3
from pathlib import Path


def generate_image_gallery(bucket: str, prefix: str = 'test/', expires_in: int = 3600):
    """Generate an HTML gallery with all images from S3"""
    s3_client = boto3.client('s3', profile_name='mechlib-dev')

    # List all objects in the prefix
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)

    # Generate pre-signed URLs for each image
    image_urls = []
    for obj in response.get('Contents', []):
        key = obj['Key']
        # Only include image files
        if key.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            image_urls.append({'key': key, 'url': url})

    # Generate image HTML
    images_html = '\n'.join([
        f'        <div class="gallery-item">\n'
        f'            <img src="{img["url"]}" alt="{img["key"]}">\n'
        f'            <p>{Path(img["key"]).name}</p>\n'
        f'        </div>'
        for img in image_urls
    ])

    # Read template and substitute images
    template_path = Path('../templates/gallery.html')
    template = template_path.read_text()
    html = template.replace('{{IMAGES}}', images_html)

    # Save to local file
    gallery_path = Path('gallery.html')
    gallery_path.write_text(html)

    print(f"✅ Gallery created at {gallery_path.absolute()}")
    print(f"📖 Open in browser: file://{gallery_path.absolute()}")
    return gallery_path
