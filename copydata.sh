kubectl cp open-webui/mynewwebui-55694b948c-mkshr:/app/backend/data ./data


kubectl cp data/uploads hrwebui/$1:/app/backend/data/uploads/
for file in `ls data/vector_db`
do
	echo $file
	kubectl cp vector_db/$file hrwebui/$1:/app/backend/data/vector_db/
done

kubectl delete pod $1 -n hrwebui
