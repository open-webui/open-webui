Our weekly meetups are [Wednesdays at NOON EDT](/io/coders/) and [Fridays at 5 PM EDT](/io/coders) and [Sundays at 10 PM EDT](/io/coders/).

<hr style="margin-bottom:20px">

# Active Projects


[Site Install](../localsite/start/steps/) - [Observable DataCommons](/data-commons/dist/) - [Open WebUI](src/) - [Storyboard Generator](/data-pipeline/research) - [Moonshots](/community/projects/)

**Chose one to fork and install locally**
- [Open WebUI (Projects)](src) with Python and [Retrieval Augmented Generation (RAG)](https://docs.openwebui.com/tutorial/rag/) like Pinecone
- [Earthscape for Chatbot AI](/earthscape/app/) - React, Supabase and [NextJS Hosting using GitHub Pages](https://www.freecodecamp.org/news/how-to-deploy-next-js-app-to-github-pages/)

**Charts, SQL, Vite, Supabase, AI Chat**
- [Sankey Industry eChart](/useeio.js/charts/echarts/sankey-nodeAlign-left.html) - eCharts uses a common echarts.min.js file which well load in [Feed Viewer](/feed/view). <!-- Chenbohan -->
- [Harmonized System (HS) codes](/requests/products/) - via Concordence R Language within Python CoLab - Song
- [Open Footprint Data in SQL](/useeio.js/footprint) - Sahil, Himanshu, Sridevi, Song
- [Feed Player](../feed/intro.html) - Video and Images - Gary, Fanyi, Marco
- [Feed Viewer](../feed/view/#feed=nasa) - JSON, YAML, CSS, RSS - Loren and Gary ([address lookup](/feed/view/#feed=311)) 
- [Datausa.io](https://datausa.io) - Add API and embeddable visualizations to Feed Player

<!--
- [Restack.io](https://www.restack.io/docs/supabase-knowledge-supabase-rust-sdk-guide) - for Supabase with Rust and Streamlit
-->

<!-- 
openai
Docker path: https://chat.openai.com/share/61b0997f-ea9b-49f7-9bcb-12fa0519a2d1 

Matthew Berman list of true Agents: 
https://youtu.be/_AOA6M9Ta2I?si=Bh8SMhyD3GmuCLks&t=378
-->

<!--
CSV Files to use for Timelines, Observable, and AI Training at: [industries/naics/US/counties](https://github.com/ModelEarth/community-data/tree/master/industries/naics/US/counties)  
Pre-processed data for county industry levels, based on employment, establishments and payroll.-->

**Machine Learning with Python and Google Data Commons**

- [RStudio - API to JSON](/localsite/info/data/flowsa/)
- [ML for Community Forecasting Timelines](../data-pipeline/timelines/)
- [RealityStream](/RealityStream/) - Machine Learning Classification Models
- [Open Footprint Panels - YAML Display](/OpenFootprint)
- [Process Industry NAICS by Zip Code](/data-pipeline/industries/naics)
- [Top Commodities by State (hide sort columns)](/data-pipeline/research/economy) - Dinesh
- [State Regions using Sets of Counties](/community-data/us/edd/) - Dinesh
- [USEEIO matrix files with clustering](/machine-learning/python/cluster/) - <!--Honglin-->Rupesh
- [CrewAI+Ollama integration](https://lightning.ai/lightning-ai/studios/ai-agents-powered-by-crewai) within our [Open WebUI fork](src)

**Observable Framework + GDC Visualization Projects**

- [Python CoLabs for GDC timeline automation - Air and Climate](/data-commons/dist/air)
- [Observable with Data Commons](/data-commons/) - [Data Loaders How-To](/data-commons/dist/air/)
- [Balanced Food](/balance/) - [World Nutrition](/data-commons/dist/food) - Kargil, Meiru
- [Chord Chart Data Prep](/io/charts/chord/) - [ask Kargil for location](https://github.com/modelearth/Observables-DataLoader/tree/master/docs)
- [International Google Data Commons API](/data-commons/) - with [Observable Data Loaders](https://observablehq.com/framework/loaders)


**BuildingTransparency and Open Footprint labels**

- [BuildingTransparency with OpenFootprint impact data](/OpenFootprint)
- [Use our state map filter](#geoview=country) with colors for [new USEEIO reporting maps](https://figshare.com/collections/USEEIO_State_Models_v1_0_-_Supporting_Figures/7041473)
- [Python - Process All the Places by State and Zip](/places) - Carolyn
- [BuildingTransparency - Product Impact Profiles by State and Zip](/io/template/feed/) - Ronan
- [BuildingTransparency - API Aggregates of States and Countries](/io/template/product/) - Previously Luwei
- [BuildingTransparency - JSON file pull for impact templates](/io/template/product/)
- [AI Process for Farm Fresh Data and Food Deserts ML](/community-data/process/python/farmfresh/)
- [Push EPA date to Google Data Commons API](https://docs.datacommons.org/api/)


**Storyboard Generator - Images and Video for Request Visualization**
- [Image Gallery (JQuery) and Video (Leonardo)](/data-pipeline/research/stream)
- [Our Storyboard Generator](/data-pipeline/research/) and [Request Visualizer for Meals and City Planning](/requests/)
- [Open Webui image generation](https://docs.openwebui.com/tutorial/images/) - Integrate our image .csv process
<!-- [Kishor's Repo](https://github.com/mannurkishorreddy/streamlit-replicate-img-app)-->
<!--- [Image Gallery (React)](/react-gallery/view/) - Anthony -->

**React, Tabulator, Industry Timelines**
- [React Team - Impact Side Navigation](/io/charts/inflow-outflow/#set=prosperity&indicators=VADD,JOBS) - Ziyao
- [React Team - Mosaic column checkboxes](/io/charts) - Fanyi
- [React Team - Commodity Totals](/localsite/info/data/totals/) in [Jobs Reports](/localsite/info/#indicators=JOBS)
- [Tabulator - Merge in industry year rows using Javascript (1-3)](/data-pipeline/timelines/tabulator/) - Rupesh<!--Vadlamudi-->
- [Tabulator - Merge in titles using Javascript (4)](/data-pipeline/timelines/tabulator/) - Dinesh, Fanyi, Rupesh
- [Steps for SQLite in Browser](/data-pipeline/timelines/sqlite/phiresky/) - [Example (Runs SQL)](https://phiresky.github.io/blog/2021/hosting-sqlite-databases-on-github-pages/) - Aashish
- [Impact Label Pipeline](/apps/impact) - Too optimize and change inputs

**Moonshot Challenges**
Are you ready to [take the leap?](/community/projects/)
<br>


# Open WebUI Install

If you don't have Ollama installed yet, you can run the following in your local projects folder.  
(If you already have an "open-webui" container in Docker, delete or rename it.)

	docker compose up -d --build

Otherwise, here are the steps [if you already have Ollama](https://docs.openwebui.com/)
Or if you're retaining an [existing open-webui container](https://docs.openwebui.com/getting-started/)
<!--
, and using GPU Support, then run:

	docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
-->

Open your local build at [localhost:3000](http://localhost:3000)

	npm run build

### Train with a web page

Type # followed by any https:// domain path to ask questions about a specific web page. 
Allow a couple minutes to process each question. You can ask questions about today's headlines:

	#https://yahoo.com

**Digesting the News (sample request)**
Create 8 categories that all news stories fall in, and calculate the percentage of stories in each category. The 8 category percentages should add up to 100%. A story can be divided among multiple categories. Then list a sample of three top stories for each of the 5 categories. Include URL links for each article listed using using markdown formatting for each of the 3 articles listed below each of the 8 categories.

<!-- npm run preview didn't have an api. flower -->

[Open WebUI Documentation](https://docs.openwebui.com/)

<div id="activeDivLoaded"></div>
