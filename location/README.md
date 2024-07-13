[Active Projects](../)
# Location tools for Open WebUI

You'll have our Open WebUI "projects" fork running at [http://localhost:3000](http://localhost:3000/).
Use the Docker install below so you can send Pull Requests to our "projects" fork.
Our Docker package resides at [https://github.com/modelearth/projects/pkgs/container/projects](https://github.com/modelearth/projects/pkgs/container/projects)

TO DO: Watch this [Open WebUI video](https://www.youtube.com/watch?v=N-aRJe--txs) and share some cool findings during our meetup.

TO DO: Set up [RAG context](https://docs.openwebui.com/tutorial/rag/) using our [superthermal evaporation](../../evaporation-kits/) page and related articles.

TO DO: Figure out how to call our "src-merged" folder rather then "src". Copy needed pages 

DONE: Manually placed localsite.js include in src-merged/app.html to add our location navigation:

	<script type="text/javascript" src="https://model.earth/localsite/js/localsite.js?showheader=true&showsearch=true"></script>

TO DO: Create a script to merge files from "location" into "src" and send to "src-merged"

TO DO: Create an example of loading a Python util file that is also loaded by our [RealityStream](../../RealityStream/) app.

TO DO: Activate hosting using Cloudflare.

TO DO: Provide a means to upload a list of members from a Google Sheet link.

TO DO: Provide a button for admins to export the list of members as a CSV file.

TO DO: Update our Readme in localsite.js to one that supports [NOTE], [WARNING], [TIP]