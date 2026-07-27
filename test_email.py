
import requests
import json

res = requests.post('http://localhost:8000/tickets/create', json={
    'topic': 'Network Issue',
    'user_priority': 'Low',
    'user_email': 'priyadharshinijsd@tsm.ac.in',
    'created_by': 'Test User',
    'description': 'Cannot connect to network'
})
data = res.json()
print('Ticket ID:', data['ticket_id'])
print('Status:', data['ticket']['status'])
print('Email sent:', data['ticket'].get('email_sent'))
print('Email status:', data['ticket'].get('email_status'))
print('Email sent to:', data['ticket'].get('user_email'))
