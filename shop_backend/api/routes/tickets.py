"""
Tickets de support côté client.

POST /tickets                → créer un ticket
GET  /tickets                 → mes tickets
GET  /tickets/{id}             → fil de discussion d'un ticket
POST /tickets/{id}/messages     → répondre à un ticket
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from models.ticket import TicketCreate, TicketMessageCreate
from models.responses import TicketPublic
from api.dependencies import get_current_customer
import db.tickets_repository as tickets_repo

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=TicketPublic, status_code=201, summary="Créer un ticket")
async def create_ticket(body: TicketCreate, customer: dict = Depends(get_current_customer)):
    tid = await tickets_repo.create(customer["username"], body.subject, body.message)
    return await tickets_repo.find_by_id(tid)


@router.get("", response_model=list[TicketPublic], summary="Mes tickets")
async def list_my_tickets(customer: dict = Depends(get_current_customer)):
    return await tickets_repo.list_for_user(customer["username"])


@router.get("/{ticket_id}", response_model=TicketPublic, summary="Fil de discussion d'un ticket")
async def get_ticket(ticket_id: str, customer: dict = Depends(get_current_customer)):
    ticket = await tickets_repo.find_by_id(ticket_id)
    if not ticket or ticket["username"] != customer["username"]:
        raise HTTPException(404, "Ticket introuvable")
    return ticket


@router.post("/{ticket_id}/messages", response_model=TicketPublic, summary="Répondre à un ticket")
async def reply_to_ticket(ticket_id: str, body: TicketMessageCreate, customer: dict = Depends(get_current_customer)):
    ticket = await tickets_repo.find_by_id(ticket_id)
    if not ticket or ticket["username"] != customer["username"]:
        raise HTTPException(404, "Ticket introuvable")
    if ticket["status"] == "closed":
        raise HTTPException(409, "Ce ticket est clos")

    await tickets_repo.add_message(ticket_id, "customer", customer["username"], body.body)
    return await tickets_repo.find_by_id(ticket_id)
