#!/usr/bin/env python3
"""
MCP Server for mechlib image search functionality.
Exposes the vector store search as an MCP tool.
"""

import logging
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from src.mechlib.vector_store import VectorStoreManager

# Configure logging to file to avoid interfering with stdio (MCP uses stdio)
logging.basicConfig(
    level=logging.INFO,
    filename='/tmp/mechlib_mcp.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("mechlib")


def linkify_text(text: str) -> str:
    """Convert URLs in text to clickable HTML links."""
    if not text:
        return text
    # Regex pattern for URLs (http, https)
    url_pattern = r'(https?://[^\s<>"]+)'
    # Replace URLs with HTML anchor tags
    return re.sub(url_pattern, r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', text)



"""

  | Threshold | What You Get                                |
  |-----------|---------------------------------------------|
  | 0.3-0.4   | Only nearly identical matches               |
  | 0.5       | Very relevant results (recommended default) |
  | 0.6-0.7   | Relevant results, some flexibility          |
  | 0.8       | Includes loosely related images             |
  | 1.0+      | Very lenient, includes distant matches      |

"""
@mcp.tool()
def search_images(query: str, k: int = 3, score_threshold: float = 0.5, use_hybrid: bool = True, keyword_weight: float = 0.5) -> str:
    """
    Search for images in the mechlib vector database using hybrid search (keyword + semantic).

    Args:
        query: Natural language search query describing the images you want to find
        k: Number of results to return (default: 3, max: 50)
        score_threshold: Maximum distance threshold (0.0-2.0). Lower = more strict filtering.
                        pgvector uses cosine distance where 0=identical, 2=opposite.
                        Recommended: 0.3-0.5 for relevant results only, 1.0 for lenient filtering.
                        Default: 0.5
        use_hybrid: Use hybrid search (keyword + semantic). Default: True
        keyword_weight: Weight for keyword search (0.0-1.0). 0.5=equal weight, 1.0=keyword only, 0.0=semantic only

    Returns:
        Path to the generated HTML gallery file
    """
    try:
        # Cap k at reasonable maximum for performance
        k = min(k, 50)
        logger.info(f"Searching for images with query: {query}, k={k}, threshold={score_threshold}, hybrid={use_hybrid}")
        vector_manager = VectorStoreManager()

        # Perform search (hybrid or semantic only)
        if use_hybrid:
            results_with_scores = vector_manager.hybrid_search(query=query, k=k, keyword_weight=keyword_weight)
        else:
            results_with_scores = vector_manager.vector_store.similarity_search_with_score(query=query, k=k)

        # Filter by distance threshold
        # pgvector returns cosine distance where: 0=identical, 1=orthogonal, 2=opposite
        # Lower distance = more similar, so we keep results where distance <= threshold
        filtered_results = []
        for doc, score in results_with_scores:
            logger.info(f"Result: {doc.metadata.get('filename')} - Distance: {score}")
            # Keep results with distance below or equal to threshold (more similar)
            if score <= score_threshold:
                filtered_results.append(doc)

        results = filtered_results

        if not results:
            total_results = len(results_with_scores)
            if total_results > 0:
                min_score = min(s for _, s in results_with_scores)
                return f"No images found matching your query with distance <= {score_threshold}.\nClosest match has distance {min_score:.3f}. Try increasing the threshold to {min_score + 0.1:.2f} or higher."
            else:
                return "No images found matching your query."

        # Log filtering stats
        logger.info(f"Filtered to {len(results)}/{len(results_with_scores)} results with distance <= {score_threshold}")

        # Generate gallery
        from src.mechlib.s3_store import S3_StoreManager
        s3_client = S3_StoreManager()

        image_urls = []
        for doc in results:
            url = s3_client.generate_presigned_url(
                s3_uri=doc.metadata.get('s3_uri'),
            )
            image_urls.append(url)

        # Generate image HTML
        images_html = '\n'.join([
            f'        <div class="gallery-item">\n'
            f'            <img src="{url}" alt="{doc.metadata.get("filename", "Image")}">\n'
            f'            <p title="{doc.metadata.get("description", "")}">{linkify_text(doc.metadata.get("description", ""))}</p>\n'
            f'        </div>'
            for url, doc in zip(image_urls, results)
        ])

        # Read template and substitute images
        # Use absolute path from mcp_server.py location
        mcp_dir = Path(__file__).parent
        template_path = mcp_dir / 'templates' / 'gallery.html'
        template = template_path.read_text()
        html = template.replace('{{IMAGES}}', images_html)

        # Save to local file in temp directory
        gallery_path = Path('/tmp/mechlib_gallery.html')
        gallery_path.write_text(html)

        return f"✅ Gallery created at {gallery_path.absolute()}\n📖 Open in browser: file://{gallery_path.absolute()}"

    except Exception as e:
        logger.error(f"Error during search: {e}", exc_info=True)
        return f"Error: {str(e)}"


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()