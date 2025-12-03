#!/usr/bin/env python3
"""
MCP Server for mechlib image search functionality.
Exposes the vector store search as an MCP tool.
"""

import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from src.vector_store import VectorStoreManager

# Configure logging to file to avoid interfering with stdio (MCP uses stdio)
logging.basicConfig(
    level=logging.INFO,
    filename='/tmp/mechlib_mcp.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("mechlib")


@mcp.tool()
def search_images(query: str, k: int = 3, score_threshold: float = 0.7) -> str:
    """
    Search for images in the mechlib vector database using semantic search.

    Args:
        query: Natural language search query describing the images you want to find
        k: Number of results to return (default: 3)
        score_threshold: Minimum similarity score (0.0-1.0). Higher = more strict.
                        Recommended: 0.5-0.7 for relevant results. Default: 0.0 (no filtering)

    Returns:
        Path to the generated HTML gallery file
    """
    try:
        logger.info(f"Searching for images with query: {query}, k={k}, threshold={score_threshold}")
        vector_manager = VectorStoreManager()

        # Perform similarity search with scores
        results_with_scores = vector_manager.vector_store.similarity_search_with_score(query=query, k=k)

        # Filter by score threshold (lower score = more similar in some distance metrics)
        # Note: Pinecone uses cosine similarity where higher is better (0-1 range)
        # But similarity_search_with_score might return distance, so we need to check
        filtered_results = []
        for doc, score in results_with_scores:
            logger.info(f"Result: {doc.metadata.get('filename')} - Score: {score}")
            # If score is above threshold, keep it
            # Note: Adjust this logic based on your distance metric
            if score >= score_threshold:
                filtered_results.append(doc)

        results = filtered_results

        if not results:
            total_results = len(results_with_scores)
            if score_threshold > 0.0:
                return f"No images found matching your query with score >= {score_threshold}.\nFound {total_results} results below threshold. Try lowering the threshold."
            else:
                return "No images found matching your query."

        # Log filtering stats
        if score_threshold > 0.0:
            logger.info(f"Filtered to {len(results)}/{len(results_with_scores)} results above threshold {score_threshold}")

        # Generate gallery
        from src.s3_store import S3_StoreManager
        s3_client = S3_StoreManager()

        image_urls = []
        for doc in results:
            url = s3_client.generate_presigned_url(
                s3_uri=doc.metadata.get('s3_uri'),
                expiration=3600
            )
            image_urls.append(url)

        # Generate image HTML
        images_html = '\n'.join([
            f'        <div class="gallery-item">\n'
            f'            <img src="{url}" alt="{doc.metadata.get("filename", "Image")}">\n'
            f'            <p>{doc.metadata.get("description", "")}</p>\n'
            f'        </div>'
            for url, doc in zip(image_urls, results)
        ])

        # Read template and substitute images
        template_path = Path('./templates/gallery.html')
        template = template_path.read_text()
        html = template.replace('{{IMAGES}}', images_html)

        # Save to local file
        gallery_path = Path('gallery.html')
        gallery_path.write_text(html)

        return f"✅ Gallery created at {gallery_path.absolute()}\n📖 Open in browser: file://{gallery_path.absolute()}"

    except Exception as e:
        logger.error(f"Error during search: {e}", exc_info=True)
        return f"Error: {str(e)}"


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()