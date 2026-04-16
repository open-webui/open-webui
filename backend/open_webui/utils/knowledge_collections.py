async def reindex_file_in_collection(
    *,
    request,
    file_id: str,
    collection_name: str,
    user,
    db,
    process_file_form_factory,
    process_file_func,
    vector_db_client,
) -> None:
    result = await vector_db_client.query(
        collection_name=collection_name,
        filter={'file_id': file_id},
    )

    existing_ids = []
    if result is not None and result.ids and result.ids[0]:
        existing_ids = list(result.ids[0])

    await process_file_func(
        request,
        process_file_form_factory(file_id=file_id, collection_name=collection_name),
        user=user,
        db=db,
    )

    if existing_ids:
        await vector_db_client.delete(
            collection_name=collection_name,
            ids=existing_ids,
        )
