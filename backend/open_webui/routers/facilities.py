from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
import os
import json
from urllib.parse import urlparse


from open_webui.models.knowledge import Knowledges
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.utils.auth import get_verified_user
from open_webui.retrieval.web.tavily import search_tavily
from open_webui.retrieval.web.main import SearchResult

# facilities prompt template
FACILITIES_PROMPT = """You are an expert grant writer specializing in the 'Facilities, Equipment, and Other Resources' section of academic proposals for NSF and NIH grants.

Your job is to expand and professionally refine the user's section draft using:
1.  User Input (this forms the base and must be preserved).
2.  PDF Research Chunks from relevant proposals or facility descriptions.
3.  Trusted Web Snippets:
   - For most sections: snippets from `nyu.edu` or `nsf.gov`.
   - For Internal Facilities (NYU): only snippets from the specified trusted NYU HPC/Core Facilities pages.


---

### FEW-SHOT GUIDANCE

**Example 1**  
> *User:* "Our Robotics Lab has 10 industrial arms and a motion capture system."  
> *Draft:* "The Robotics Lab features 10 industrial-grade robotic manipulators and an advanced OptiTrack motion capture system for multi-agent interaction studies [1]."

**Example 2**  
> *User:* "We use NYU's HPC system with 1000 GPUs."  
> *Draft:* "High-performance computing is supported by NYU's HPC cluster with 1,024 NVIDIA A100 GPUs [2]."

---

### SECTION: {section}

**User Input:**
\"\"\"
{user_input}
\"\"\"

**PDF Research Chunks:**
\"\"\"
{retrieved_chunks}
\"\"\"

**Web Snippets**
\"\"\"
{web_snippets}
\"\"\"

---

### INSTRUCTIONS
- Start with the User Input, retain all core ideas.
- Expand with factual, cited data from PDF Chunks or Web Snippets.
- Cite all sources using: [source_id] format (e.g., [1], [2]) when source tags are provided.
- Never invent or assume data not present in input or sources.
- If no relevant info is found, return only the user's input — improved stylistically.

Write a polished section suitable for direct inclusion in an NSF or NIH grant.
"""

router = APIRouter()

class FacilitiesRequest(BaseModel):
    sponsor: str  
    form_data: Dict[str, str]  
    model: str  
    web_search_enabled: bool = False  

class FacilitiesResponse(BaseModel):
    success: bool
    message: str
    content: str 
    sources: List[Dict]  
    sections: Dict[str, str]  
    error: Optional[str] = None

def get_section_labels(sponsor: str) -> List[str]:
    """Get section labels based on sponsor type"""
    nsf_sections = [
        "1. Project Title",
        "2. Research Space and Facilities",
        "3. Core Instrumentation", 
        "4. Computing and Data Resources",
        "5a. Internal Facilities (NYU)",
        "5b. External Facilities (Other Institutions)",
        "6. Special Infrastructure"
    ]
    
    if sponsor == "NIH":
        return nsf_sections + ["7. Equipment"]
    else:
        return nsf_sections

def facilities_web_search(query: str, request: Request, user) -> tuple[str, List[str]]:
    """
     web search for facilities - uses existing NAGA Tavily configuration
    """
    try:
    
        if not request.app.state.config.TAVILY_API_KEY:
            logging.warning("TAVILY_API_KEY not configured in NAGA")
            return "", []
        
        tavily_api_key = request.app.state.config.TAVILY_API_KEY.get(user.email)
        if not tavily_api_key:
            logging.warning(f"No Tavily API key found for user: {user.email}")
            return "", []
        
        logging.info(f"Starting facilities web search for query: {query}")
        
        allowed_domains = ["nyu.edu", "nsf.gov"]
        blocklist = [
            "https://med.nyu.edu/research/scientific-cores-shared-resources/high-performance-computing-core"
        ]
        
        snippets = []
        urls = []
        
        for domain in allowed_domains:
            logging.info(f"Searching domain: {domain}")
            try:
                results = search_tavily(
                    api_key=tavily_api_key,
                    query=query,
                    count=3,
                    filter_list=[domain]
                )
                logging.info(f"Search results for {domain}: {len(results) if results else 0} results")
                
                if results:
                    for result in results:
                        url = result.link.strip()
                        content = result.snippet.strip()
                        logging.info(f"Found result: {url[:50]}...")
                        
                        
                        if not any(url.startswith(bad) for bad in blocklist):
                            snippets.append(f"{content}\n(Web Source: {url})")
                            urls.append(url)
                            logging.info(f"Added to results: {url}")
                        else:
                            logging.info(f"Blocked by filter: {url}")
                else:
                    logging.info(f"No results for domain: {domain}")
            except Exception as e:
                logging.error(f"Error searching domain {domain}: {e}")
        
        return "\n\n".join(snippets), urls
        
    except Exception as e:
        logging.error(f"Facilities web search failed: {e}")
        return f"Web search failed: {e}", []

def facilities_web_search_specific_sites(query: str, allowed_sites: List[str], request: Request, user) -> tuple[str, List[str]]:
    """
    web search within specific sites - uses existing NAGA Tavily configuration
    """
    try:
       
        if not request.app.state.config.TAVILY_API_KEY:
            logging.warning("TAVILY_API_KEY not configured in NAGA")
            return "", []
        
        
        tavily_api_key = request.app.state.config.TAVILY_API_KEY.get(user.email)
        if not tavily_api_key:
            logging.warning(f"No Tavily API key found for user: {user.email}")
            return "", []
        
        logging.info(f"Starting specific sites web search for query: {query}, sites: {allowed_sites}")
        
        snippets = []
        urls = []
        
        
        for site in allowed_sites:
            
            domain = urlparse(site).netloc
            results = search_tavily(
                api_key=tavily_api_key,
                query=query,
                count=3,
                filter_list=[domain]
            )
            
            for result in results:
                url = result.link
                content = result.snippet.strip()
                
                if any(url.startswith(s) for s in allowed_sites):
                    snippets.append(f"{content}\n(Web Source: {url})")
                    urls.append(url)
        
        return "\n\n".join(snippets), urls
        
    except Exception as e:
        logging.error(f"Facilities specific site web search failed: {e}")
        return f"Web search failed: {e}", []

def search_knowledge_base(query: str, user_id: str, request: Request, k: int = 5) -> List[tuple]:
    """Simple knowledge base search"""
    try:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(user_id, "read")
        collection_names = [kb.id for kb in knowledge_bases]
        
        if not collection_names:
            logging.warning("No knowledge bases found for user")
            return []
        
        try:
            embedding_function = request.app.state.EMBEDDING_FUNCTION
            query_embedding = embedding_function(query, user_id)
        except Exception as e:
            logging.error(f"Failed to generate embeddings: {e}")
            return []
        
        
        results = []
        for collection_name in collection_names:
            try:
               
                search_results = VECTOR_DB_CLIENT.search(
                    collection_name=collection_name,
                    vectors=[query_embedding],
                    limit=k * 3  
                )
                
                if search_results and hasattr(search_results, 'documents') and search_results.documents:
                    documents = search_results.documents[0]
                    metadatas = search_results.metadatas[0] if search_results.metadatas else []
                    
                    for i, doc in enumerate(documents):
                        if i < len(metadatas) and metadatas[i]:
                            
                            metadata = metadatas[i]
                            source = 'unknown'
                            
                            logging.info(f"Metadata for document {i}: {metadata}")
                            
                            
                            for key in ['source', 'name', 'filename', 'file_name']:
                                if key in metadata:
                                    source = metadata[key]
                                    logging.info(f"Found source '{source}' using key '{key}'")
                                    break
                        else:
                            source = 'unknown'
                            logging.warning(f"No metadata found for document {i}")
                        results.append((doc, source))
                        
            except Exception as e:
                logging.warning(f"Failed to search collection {collection_name}: {e}")
                continue
        
        return results[:k]
        
    except Exception as e:
        logging.error(f"Knowledge base search failed: {e}")
        return []

async def call_llm_direct(prompt: str, model: str, user, request: Request) -> str:
    """Direct LLM call using existing chat completion system"""
    try:
        from open_webui.utils.chat import generate_chat_completion
        
        form_data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        completion_response = await generate_chat_completion(
            request=request,
            form_data=form_data,
            user=user,
            bypass_filter=True
        )
        

        if isinstance(completion_response, dict) and "choices" in completion_response:
            return completion_response["choices"][0]["message"]["content"].strip()
        else:
            raise Exception(f"Unexpected LLM response format: {type(completion_response)}")
            
    except Exception as e:
        logging.error(f"Direct LLM call failed: {e}")
        raise Exception(f"LLM call failed: {str(e)}")

@router.post("/generate", response_model=FacilitiesResponse)
async def generate_facilities_response(request: Request, form_data: FacilitiesRequest, user=Depends(get_verified_user)):
    """
    Generate facilities response
    Only works when facilities is enabled for the user
    """
    if not request.app.state.config.ENABLE_FACILITIES.get(user.email):
        raise HTTPException(status_code=403, detail="Facilities feature is not enabled for this user")
    try:
        if form_data.sponsor not in ["NSF", "NIH"]:
            raise HTTPException(status_code=400, detail="Invalid sponsor. Must be 'NSF' or 'NIH'")
        
        section_labels = get_section_labels(form_data.sponsor)
        
        field_mappings = {
            "projectTitle": "1. Project Title",
            "researchSpaceFacilities": "2. Research Space and Facilities", 
            "coreInstrumentation": "3. Core Instrumentation",
            "computingDataResources": "4. Computing and Data Resources",
            "internalFacilitiesNYU": "5a. Internal Facilities (NYU)",
            "externalFacilitiesOther": "5b. External Facilities (Other Institutions)",
            "specialInfrastructure": "6. Special Infrastructure",
            "equipment": "7. Equipment"
        }
        
       
        user_inputs = {}
        for form_key, section_label in field_mappings.items():
            if form_key in form_data.form_data and section_label in section_labels:
                user_inputs[section_label] = form_data.form_data[form_key].strip()
        
        if not any(user_inputs.values()):
            return FacilitiesResponse(
                success=False,
                message="No input provided in form fields",
                sections={},
                sources=[],
                error="Please fill in at least one form field"
            )
        
        
        section_outputs = {}
        all_sources = []
        source_index = 1  
        
        for section, user_text in user_inputs.items():
            if not user_text:
                continue
            
            logging.info(f"Processing section: {section}")
            logging.info(f"Web search enabled flag: {form_data.web_search_enabled}")
            
            query = f"{section}: {user_text}"
            
            
            search_results = search_knowledge_base(query, user.id, request, k=5)
            
             
            retrieved_chunks = []
            section_sources = []
            
            
            source_groups = {}
            for doc, source in search_results:
                if source not in source_groups:
                    source_groups[source] = []
                source_groups[source].append(doc)
            
            for source, docs in source_groups.items():
                # Use the same source_index for all documents from this source
                current_source_index = source_index
                logging.info(f"Processing source '{source}' with {len(docs)} documents, using citation index {current_source_index}")
                
                for doc in docs:
                    retrieved_chunks.append(f"<source><source_id>{current_source_index}</source_id><source_context>{doc}</source_context></source>")
                
                mock_distances = [0.15] * len(docs)  
                
                section_sources.append({
                    "source": {"name": source},
                    "document": docs,  
                    "metadata": [{"source": source, "name": source}] * len(docs),
                    "distances": mock_distances 
                })
                source_index += 1
            
            retrieved_texts_with_sources = "\n\n".join(retrieved_chunks) if retrieved_chunks else "No relevant PDF documents found in knowledge base."
            all_sources.extend(section_sources)
            
            logging.info(f"Found {len(search_results)} chunks for {section}")
            logging.info(f"Sources found: {[source for _, source in search_results]}")
            
            # web search only if enabled
            web_content = ""
            web_links = []
            web_source_tags = []
            
            if form_data.web_search_enabled:
                logging.info(f"Web search enabled for section: {section}")
                if section == "5a. Internal Facilities (NYU)":
                    allowed_sites = [
                        "https://sites.google.com/nyu.edu/nyu-hpc/",
                        "https://www.nyu.edu/life/information-technology/research-computing-services/high-performance-computing.html",
                        "https://www.nyu.edu/life/information-technology/research-computing-services/high-performance-computing/high-performance-computing-nyu-it.html"
                    ]
                    logging.info(f"Using specific sites search for NYU Internal Facilities")
                    web_content, web_links = facilities_web_search_specific_sites(
                        query, allowed_sites, request, user
                    )
                else:
                    # Standard web search for other sections
                    logging.info(f"Using standard web search for section: {section}")
                    web_content, web_links = facilities_web_search(query, request, user)
                
                logging.info(f"Web search results - Content length: {len(web_content) if web_content else 0}, Links: {len(web_links) if web_links else 0}")
                
                # Format web content with source tags and add to sources
                if web_content and web_links:
                    
                    web_content_parts = web_content.split('\n\n---\n\n')
                    
                    for i, (content_part, url) in enumerate(zip(web_content_parts, web_links)):
                        if content_part.strip() and url.strip():
                            # Use current source_index for this web source
                            current_web_source_index = source_index
                            logging.info(f"Processing web source '{url}' using citation index {current_web_source_index}")
                            web_source_tags.append(f"<source><source_id>{current_web_source_index}</source_id><source_context>{content_part.strip()}</source_context></source>")
                            

                            web_distances = [0.1] 
                            
                            # Create separate source for each URL (like existing NAGA system)
                            all_sources.append({
                                "source": {"name": url, "url": url},  # Use URL as both name and url
                                "document": [content_part.strip()],
                                "metadata": [{"source": url, "name": url}],
                                "distances": web_distances  # Add distances for match percentages
                            })
                            source_index += 1
                
                logging.info(f"Found {len(web_links)} web sources for {section}")
            else:
                logging.info(f"Web search disabled for {section}")
            
            # knowledge base + web
            all_source_tags = retrieved_chunks + web_source_tags
            combined_sources = "\n\n".join(all_source_tags) if all_source_tags else "No relevant sources found."
            
            prompt = FACILITIES_PROMPT.format(
                section=section,
                user_input=user_text,
                retrieved_chunks=combined_sources,
                web_snippets="" 
            )
            
            try:
                generated_content = await call_llm_direct(prompt, form_data.model, user, request)
                
                import re
                cleaned_content = generated_content.strip()
                
                if cleaned_content.startswith('Error:') or 'Connection aborted' in cleaned_content:
                    logging.warning(f"LLM returned error for {section}, using user input as fallback")
                    section_outputs[section] = user_text
                else:
                    section_outputs[section] = cleaned_content
                    logging.info(f"Generated content for {section}: {len(cleaned_content)} chars")
                    logging.info(f"Content preview: {cleaned_content[:200]}...")
                
            except Exception as e:
                logging.error(f"Failed to generate content for {section}: {e}")
                section_outputs[section] = user_text
        
        if not section_outputs:
            return FacilitiesResponse(
                success=False,
                message="No sections generated",
                content="",
                sections={},
                sources=[],
                error="Failed to generate any sections"
            )
        
        content = f"# Facilities Response for {form_data.sponsor}\n\n"
        
        for section_name, section_content in section_outputs.items():
            content += f"## {section_name}\n\n{section_content}\n\n"
        
        formatted_sources = all_sources
        logging.info(f"Final sources count: {len(formatted_sources)}")
        logging.info(f"Final sources: {[s.get('source', {}).get('name', 'unknown') for s in formatted_sources]}")
        
        return FacilitiesResponse(
            success=True,
            message=f"Successfully generated {len(section_outputs)} sections for {form_data.sponsor}",
            content=content,
            sections=section_outputs, 
            sources=formatted_sources
        )
        
    except Exception as e:
        logging.error(f"Error in facilities generation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/sections/{sponsor}")
async def get_facilities_sections(sponsor: str, request: Request, user=Depends(get_verified_user)):
    """
    Get the section labels for a specific sponsor
    Only works when facilities is enabled for the user
    """
    if not request.app.state.config.ENABLE_FACILITIES.get(user.email):
        raise HTTPException(status_code=403, detail="Facilities feature is not enabled for this user")
    try:
        if sponsor not in ["NSF", "NIH"]:
            raise HTTPException(status_code=400, detail="Invalid sponsor. Must be 'NSF' or 'NIH'")
        
        section_labels = get_section_labels(sponsor)
        
        return {
            "success": True,
            "sponsor": sponsor,
            "sections": section_labels
        }
        
    except Exception as e:
        logging.error(f"Error getting sections for {sponsor}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sections: {str(e)}")

@router.post("/web-search")
async def facilities_web_search_endpoint(request: Request, form_data: dict, user=Depends(get_verified_user)):
    """
    web search endpoint specifically for facilities - uses existing NAGA Tavily configuration
    Only works when facilities is enabled for the user
    """
    if not request.app.state.config.ENABLE_FACILITIES.get(user.email):
        raise HTTPException(status_code=403, detail="Facilities feature is not enabled for this user")
    try:
        query = form_data.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Perform standalone web search with domain filtering
        web_content, web_links = facilities_web_search(query, request, user)
        
        return {
            "success": True,
            "content": web_content,
            "sources": web_links,
            "query": query
        }
        
    except Exception as e:
        logging.error(f"Facilities standalone web search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Web search failed: {str(e)}")

# @router.post("/reindex")
# async def reindex_facilities_pdfs(request: Request, user=Depends(get_verified_user)):
#     """
#     Reindex PDFs in the knowledge base for facilities
#     Only works when facilities is enabled for the user
#     """
#     # Check if facilities is enabled for this user
#     if not request.app.state.config.ENABLE_FACILITIES.get(user.email):
#         raise HTTPException(status_code=403, detail="Facilities feature is not enabled for this user")
#     try:
#         # This would trigger a reindexing of PDFs in the knowledge base
#         # For now, return a success message
#         logging.info(f"Reindexing PDFs for user {user.id}")
        
#         return {
#             "success": True,
#             "message": "PDFs reindexed successfully"
#         }
        
#     except Exception as e:
#         logging.error(f"Error reindexing PDFs: {e}")
#         raise HTTPException(status_code=500, detail=f"Failed to reindex PDFs: {str(e)}")