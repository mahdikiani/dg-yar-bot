from fastapi import APIRouter


def get_reverse_url(name: str, router: APIRouter, **kwargs) -> str:
    for route in router.routes:
        if route.name == name:
            return route.path.format(**kwargs)
