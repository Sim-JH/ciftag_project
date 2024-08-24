from ciftag.exceptions import CiftagAPIException
from ciftag.models import (
    UserInfo,
    CredentialInfo
)
from ciftag.web.crud.core import (
    select_orm,
    search_orm,
    insert_orm,
    update_orm,
    delete_orm
)


async def get_cred_info_service(user_pk: int):
    if user_pk == 0:
        result = select_orm(CredentialInfo)
    else:
        result = search_orm(CredentialInfo, 'user_pk', user_pk)

    return result


def add_cred_info_service(user_pk, request):
    user_id = search_orm(UserInfo, 'id', user_pk, 'id', 'scalar')

    if user_id is None:
        raise CiftagAPIException('User Not Exist', 404)

    request = request.dict()
    request['user_pk'] = user_pk
    result = insert_orm(CredentialInfo, request, True)

    return result


def put_cred_info_service(user_pk: int, cred_pk: int, request):
    # admin을 제외한 사용자는 본인의 인증 정보만 수정 가능
    if not user_pk == 1:
        user_id = search_orm(CredentialInfo, 'id', cred_pk, 'user_pk', 'scalar')

        if user_id is None:
            raise CiftagAPIException('Credential Not Exist', 404)

        if user_pk != int(user_id):
            raise CiftagAPIException('Credential Not Belong In User', 401)

    result = update_orm(CredentialInfo, 'id', cred_pk, request)

    if int(result) > 0:
        return True
    else:
        return False


def delete_cred_info_service(user_pk: int, cred_pk: int):
    # admin을 제외한 사용자는 본인의 인증 정보만 삭제 가능
    if not user_pk == 0:
        user_id = search_orm(CredentialInfo, 'id', cred_pk, 'user_pk', 'scalar')

        if user_id is None:
            raise CiftagAPIException('Credential Not Exist', 400)

        if user_pk != int(user_id):
            raise CiftagAPIException('Credential Not Belong In User', 401)

    result = delete_orm(CredentialInfo, 'id', cred_pk)

    if int(result) > 0:
        return True
    else:
        return False


