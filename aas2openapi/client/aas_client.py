from __future__ import annotations

import os
from typing import List
from basyx.aas import model
from dotenv import load_dotenv

import aas2openapi
from aas2openapi.client.submodel_client import get_all_basyx_submodels_from_server, post_submodel_to_server, put_submodel_to_server
from aas2openapi.convert.convert_pydantic import ClientModel, get_vars
from aas2openapi.models import base
from aas2openapi.util import client_utils, convert_util


from ba_syx_aas_repository_client import Client as AASClient
from ba_syx_aas_repository_client.api.asset_administration_shell_repository_api import delete_asset_administration_shell_by_id, get_all_asset_administration_shells, get_asset_administration_shell_by_id, post_asset_administration_shell, put_asset_administration_shell_by_id
from fastapi import HTTPException


load_dotenv()
AAS_SERVER_ADRESS = "http://" + os.getenv("AAS_SERVER_HOST") + ":" + os.getenv("AAS_SERVER_PORT")
SUBMODEL_SERVER_ADRESS = "http://" + os.getenv("SUBMODEL_SERVER_HOST") + ":" + os.getenv("SUBMODEL_SERVER_PORT")



async def aas_is_on_server(aas_id: str) -> bool:
    """
    Function to check if an AAS with the given id is on the server
    Args:
        aas_id (str): id of the AAS
    Returns:
        bool: True if AAS is on server, False if not
    """
    try:
        await get_aas_from_server(aas_id)
        return True
    except Exception as e:
        return False


async def post_aas_to_server(aas: base.AAS):
    """
    Function to post an AAS to the server
    Args:
        aas (base.AAS): AAS to post
    Raises:
        HTTPException: If AAS with the given id already exists
    """
    if await aas_is_on_server(aas.id_):
        raise HTTPException(
            status_code=400, detail=f"AAS with id {aas.id_} already exists"
        )
    obj_store = aas2openapi.convert_pydantic_model_to_aas(aas)
    basyx_aas = obj_store.get(aas.id_)
    aas_for_client = ClientModel(basyx_object=basyx_aas)
    client = AASClient(AAS_SERVER_ADRESS)
    response = await post_asset_administration_shell.asyncio(
        client=client, json_body=aas_for_client
    )

    aas_attributes = get_vars(aas)
    for submodel in aas_attributes.values():
        await post_submodel_to_server(submodel)


async def put_aas_to_server(aas: base.AAS):
    """
    Function to put an AAS to the server
    Args:
        aas (base.AAS): AAS to put
    Raises:
        HTTPException: If AAS with the given id does not exist
    """
    if not await aas_is_on_server(aas.id_):
        raise HTTPException(
            status_code=400, detail=f"AAS with id {aas.id_} does not exist"
        )
    obj_store = aas2openapi.convert_pydantic_model_to_aas(aas)
    basyx_aas = obj_store.get(aas.id_)
    aas_for_client = ClientModel(basyx_object=basyx_aas)
    client = AASClient(AAS_SERVER_ADRESS)
    base_64_id = client_utils.get_base64_from_string(aas.id_)
    await put_asset_administration_shell_by_id.asyncio(
        aas_identifier=base_64_id, client=client, json_body=aas_for_client
    )

    submodels = convert_util.get_all_submodels_from_object_store(obj_store)
    for submodel in submodels:
        put_submodel_to_server(submodel)


async def get_basyx_aas_from_server(aas_id: str) -> model.AssetAdministrationShell:
    """
    Function to get an AAS from the server
    Args:
        aas_id (str): id of the AAS
    Raises:
        HTTPException: If AAS with the given id does not exist
    Returns:
        model.AssetAdministrationShell: AAS retrieved from the server
    """
    client = AASClient(AAS_SERVER_ADRESS)
    base_64_id = client_utils.get_base64_from_string(aas_id)
    try:
        aas_data = await get_asset_administration_shell_by_id.asyncio(
            client=client, aas_identifier=base_64_id
        )
        return client_utils.transform_client_to_basyx_model(aas_data.to_dict())
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"AAS with id {aas_id} does not exist"
        )


async def get_aas_from_server(aas_id: str) -> base.AAS:
    """
    Function to get an AAS from the server
    Args:
        aas_id (str): id of the AAS
    Returns:
        base.AAS: AAS retrieved from the server
    """
    aas = await get_basyx_aas_from_server(aas_id)
    aas_submodels = await get_all_basyx_submodels_from_server(aas)
    obj_store = model.DictObjectStore()
    obj_store.add(aas)
    [obj_store.add(submodel) for submodel in aas_submodels]

    model_data = aas2openapi.convert_object_store_to_pydantic_models(obj_store).pop()
    return model_data


async def delete_aas_from_server(aas_id: str):
    """
    Function to delete an AAS from the server
    Args:
        aas_id (str): id of the AAS
    """
    client = AASClient(AAS_SERVER_ADRESS)
    base_64_id = client_utils.get_base64_from_string(aas_id)
    response = await delete_asset_administration_shell_by_id.asyncio(
        client=client, aas_identifier=base_64_id
    )


async def get_all_aas_from_server() -> List[base.AAS]:
    """
    Function to get all AAS from the server
    Returns:
        List[base.AAS]: List of AAS retrieved from the server
    """
    client = AASClient(AAS_SERVER_ADRESS)
    result_string = await get_all_asset_administration_shells.asyncio(client=client)
    aas_data = result_string["result"]
    aas_list = [client_utils.transform_client_to_basyx_model(aas) for aas in aas_data]

    submodels = []
    for aas in aas_list:
        aas_submodels = await get_all_basyx_submodels_from_server(aas)
        submodels.extend(aas_submodels)
    obj_store = model.DictObjectStore()
    [obj_store.add(aas) for aas in aas_list]
    [obj_store.add(submodel) for submodel in submodels if not any(submodel.id == other_sm.id for other_sm in obj_store)]

    model_data = aas2openapi.convert_object_store_to_pydantic_models(obj_store)
    return model_data