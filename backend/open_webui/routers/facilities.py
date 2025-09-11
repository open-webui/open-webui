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
> *Context:* `<source><source_id>Robotics_Lab_Equipment.pdf</source_id><source_context>Lab has 10 KUKA robotic arms and OptiTrack system</source_context></source>`
> *Draft:* "The Robotics Lab features 10 industrial-grade robotic manipulators and an advanced OptiTrack motion capture system for multi-agent interaction studies [Robotics_Lab_Equipment.pdf]."

**Example 2**  
> *User:* "We use NYU's HPC system with 1000 GPUs."  
> *Context:* `<source><source_id>https://www.nyu.edu/hpc</source_id><source_context>NYU HPC cluster with 1,024 NVIDIA A100 GPUs</source_context></source>`
> *Draft:* "High-performance computing is supported by NYU's HPC cluster with 1,024 NVIDIA A100 GPUs [https://www.nyu.edu/hpc]."

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
- Use specific technical details, numbers, and concrete information from the sources.
- Write comprehensive, detailed content that demonstrates expertise and thoroughness.
**CRITICAL CITATION RULES - FOLLOW EXACTLY:**
- **MANDATORY: You MUST use source names/links in square brackets like [filename.pdf] or [https://url.com].**
- **ONLY use source names/links that appear in `<source_id>` tags in the context above.**
- **Look at the context above and find the exact `<source_id>` values.**
- **If you see `<source><source_id>HRamani_NSFCAREER_SUBMITTED_Proposal_20240723_NSF.pdf</source_id>`, you MUST use [HRamani_NSFCAREER_SUBMITTED_Proposal_20240723_NSF.pdf].**
- **If you see `<source><source_id>https://www.nyu.edu/hpc</source_id>`, you MUST use [https://www.nyu.edu/hpc].**
- **NEVER use numbered citations like [1], [2], [3] - ALWAYS use the actual source name/link.**
- **Do NOT use source names/links that are NOT in the `<source_id>` tags.**
- **If no `<source_id>` tags are provided, do not include any citations.**
- Never invent or assume data not present in input or sources.
- If no relevant info is found, return only the user's input — improved stylistically.
- Focus on creating professional, grant-worthy content that showcases facilities and capabilities.

Write a polished, comprehensive section suitable for direct inclusion in an NSF or NIH grant.
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

def facilities_web_search(query: str, request: Request, user) -> tuple[str, List[str], List[float]]:
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
        scores = []
        
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
                        score = result.score if hasattr(result, 'score') else 0.1
                        logging.info(f"Found result: {url[:50]}... with score: {score}")
                        
                        
                        if not any(url.startswith(bad) for bad in blocklist):
                            snippets.append(content)
                            urls.append(url)
                            scores.append(score)
                            logging.info(f"Added to results: {url} with score: {score}")
                        else:
                            logging.info(f"Blocked by filter: {url}")
                else:
                    logging.info(f"No results for domain: {domain}")
            except Exception as e:
                logging.error(f"Error searching domain {domain}: {e}")
        
        return "\n\n".join(snippets), urls, scores
        
    except Exception as e:
        logging.error(f"Facilities web search failed: {e}")
        return f"Web search failed: {e}", [], []

def facilities_web_search_specific_sites(query: str, allowed_sites: List[str], request: Request, user) -> tuple[str, List[str], List[float]]:
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
        scores = []
        
        
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
                score = result.score if hasattr(result, 'score') else 0.1
                
                if any(url.startswith(s) for s in allowed_sites):
                    snippets.append(content)
                    urls.append(url)
                    scores.append(score)
        
        return "\n\n".join(snippets), urls, scores
        
    except Exception as e:
        logging.error(f"Facilities specific site web search failed: {e}")
        return f"Web search failed: {e}", [], []

def search_knowledge_base(query: str, user_id: str, request: Request, k: int = 5) -> List[tuple]:
    """Simple knowledge base search with real relevance scores"""
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
                    distances = search_results.distances[0] if hasattr(search_results, 'distances') and search_results.distances else []
                    
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
                        
                        # Get real distance/score if available
                        real_score = distances[i] if i < len(distances) else 0.15
                        results.append((doc, source, real_score))
                        
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
        cited_sources = set()  # Track which sources are actually cited in the text
        # Using source names directly - frontend will handle the mapping  
        
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
            for doc, source, score in search_results:
                if source not in source_groups:
                    source_groups[source] = []
                source_groups[source].append((doc, score))
            
            for source, docs_with_scores in source_groups.items():
                
                logging.info(f"Processing source '{source}' with {len(docs_with_scores)} documents, using source name directly")
                
                docs = [doc for doc, score in docs_with_scores]
                real_distances = [score for doc, score in docs_with_scores]
                
                for doc in docs:
                    retrieved_chunks.append(f"<source><source_id>{source}</source_id><source_context>{doc}</source_context></source>")
                
                section_sources.append({
                    "source": {"name": source},
                    "document": docs,  
                    "metadata": [{"source": source, "name": source}] * len(docs),
                    "distances": real_distances 
                })
                # No need to increment since we're using source names directly
            
            retrieved_texts_with_sources = "\n\n".join(retrieved_chunks) if retrieved_chunks else "No relevant PDF documents found in knowledge base."
            all_sources.extend(section_sources)
            
            logging.info(f"Added {len(section_sources)} sources to all_sources for {section}")
            logging.info(f"Sources added: {[s.get('source', {}).get('name', 'unknown') for s in section_sources]}")
            
            logging.info(f"Found {len(search_results)} chunks for {section}")
            logging.info(f"Sources found: {[source for _, source, _ in search_results]}")
            
            web_content = ""
            web_links = []
            web_scores = []
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
                    web_content, web_links, web_scores = facilities_web_search_specific_sites(
                        query, allowed_sites, request, user
                    )
                else:

                    logging.info(f"Using standard web search for section: {section}")
                    web_content, web_links, web_scores = facilities_web_search(query, request, user)
                
                logging.info(f"Web search results - Content length: {len(web_content) if web_content else 0}, Links: {len(web_links) if web_links else 0}")
                
                if web_content and web_links:
                    
                    web_content_parts = web_content.split('\n\n')
                    
                    for i, (content_part, url, score) in enumerate(zip(web_content_parts, web_links, web_scores)):
                        if content_part.strip() and url.strip():
                            # Use current source_index for this web source
                            logging.info(f"Processing web source '{url}' using URL directly with score: {score}")
                            web_source_tags.append(f"<source><source_id>{url}</source_id><source_context>{content_part.strip()}</source_context></source>")
                            

                            web_distances = [score]  # Use real score from web search
                            
                            # Create separate source for each URL (like existing NAGA system)
                            all_sources.append({
                                "source": {"name": url, "url": url},  # Use URL as both name and url
                                "document": [content_part.strip()],
                                "metadata": [{"source": url, "name": url}],
                                "distances": web_distances  # Use real distances/scores
                            })
                            logging.info(f"Added web source to all_sources: {url}")
                            # No need to increment since we're using source names directly
                
                logging.info(f"Found {len(web_links)} web sources for {section}")
                logging.info(f"Web URLs found: {web_links}")
            else:
                logging.info(f"Web search disabled for {section}")
            
            pdf_sources = "\n\n".join(retrieved_chunks) if retrieved_chunks else "No relevant PDF documents found in knowledge base."
            web_sources = "\n\n".join(web_source_tags) if web_source_tags else "No relevant web sources found."
            
            prompt = FACILITIES_PROMPT.format(
                section=section,
                user_input=user_text,
                retrieved_chunks=pdf_sources,
                web_snippets=web_sources 
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
                    
                    # Extract cited sources from the generated text
                    import re
                    # Find all citations in the format [source_name] or [url]
                    citations = re.findall(r'\[([^\]]+)\]', cleaned_content)
                    for citation in citations:
                        # Only add if it looks like a source (contains .pdf, .doc, http, or is a filename)
                        if ('.pdf' in citation or '.doc' in citation or 
                            citation.startswith('http') or 
                            len(citation) > 10):  # Likely a filename
                            cited_sources.add(citation)
                    
                    logging.info(f"Generated content for {section}: {len(cleaned_content)} chars")
                    logging.info(f"All citations found in {section}: {citations}")
                    valid_citations = [c for c in citations if '.pdf' in c or '.doc' in c or c.startswith('http') or len(c) > 10]
                    logging.info(f"Valid source citations in {section}: {valid_citations}")
                    
                    # Separate PDF and web citations for better debugging
                    pdf_citations = [c for c in valid_citations if '.pdf' in c or '.doc' in c]
                    web_citations = [c for c in valid_citations if c.startswith('http')]
                    logging.info(f"PDF citations in {section}: {pdf_citations}")
                    logging.info(f"Web citations in {section}: {web_citations}")
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
        
        # Filter sources to only include those that were actually cited in the text
        filtered_sources = []
        for source in all_sources:
            source_name = source.get('source', {}).get('name', '')
            if source_name in cited_sources:
                filtered_sources.append(source)
        
        formatted_sources = filtered_sources
        logging.info(f"Total sources found: {len(all_sources)}")
        logging.info(f"Sources actually cited: {len(cited_sources)}")
        logging.info(f"Final sources count: {len(formatted_sources)}")
        logging.info(f"Cited sources: {list(cited_sources)}")
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

