[Active Projects](../)
# Location Projects for Open WebUI

Use our [Install Steps](setup) and send Pull Requests for our "[projects/location](https://github.com/ModelEarth/projects/tree/main/location/)" folder.  

TO DO: Watch this [Open WebUI video](https://www.youtube.com/watch?v=N-aRJe--txs) and share some cool findings during our meetup.  
The video's steps for downloading Ollama and Docker are on our [Docker Setup](setup/docker).  
If you're installing the buildable version with our [Install for Building Locally](setup), you can skip the Ollama and Docker install.

TO DO: Figure out how to call our "src-merged" folder during build rather then "src". 



TO DO: Create a script to merge files from "location" into "src" and send to "src-merged"

TO DO: Set up [RAG context](https://docs.openwebui.com/tutorial/rag/) using our [Supabase International Trade Flow](../../OpenFootprint/prep/sql/supabase/) data.

TO DO: Set up [RAG context](https://docs.openwebui.com/tutorial/rag/) using our [superthermal evaporation](../../evaporation-kits/) page and related articles.

TO DO: Create an example of loading a Python util file that is also loaded by our [RealityStream](../../RealityStream/) app.

<!--TO DO: Activate hosting using Cloudflare.-->

TO DO: Provide a means to upload a list of members from a Google Sheet link.

TO DO: Provide a button for admins to export the list of members as a CSV file.

TO DO: Update our Readme in localsite.js to one that supports [NOTE], [WARNING], [TIP]

DONE: The localsite.js is commented out in src-merged/app.html until adjustments are made to prevent overlaps.

	<script type="text/javascript" src="https://model.earth/localsite/js/localsite.js?showheader=true&showsearch=true"></script>