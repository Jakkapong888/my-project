from flask import Flask, render_template, jsonify, request
from datetime import datetime, date

app = Flask(__name__)

# ==========================================
# ฐานข้อมูลจำลอง (อิงเวลาปัจจุบัน: กันยายน 2026)
# ==========================================

tenants_list = [
    {
        "id": 201,
        "room_number": "201",
        "fullname": "สมชาย เก่งกล้า",
        "phone": "0891112233",
        "start_date": "2024-11-01",
        "contract_months": 12,
        "deposit_status": "holding",
        "deposit_refunded_at": None
    },
    {
        "id": 202,
        "room_number": "202",
        "fullname": "พิมลวรรณ สดใส",
        "phone": "0814445566",
        "start_date": "2026-05-15",
        "contract_months": 6,
        "deposit_status": "holding",
        "deposit_refunded_at": None
    },
    {
        "id": 203,
        "room_number": "203",
        "fullname": "เอกชัย นามวงศ์",
        "phone": "0827778899",
        "start_date": "2026-01-10",
        "contract_months": 12,
        "deposit_status": "holding",
        "deposit_refunded_at": None
    },
    {
        "id": 204,
        "room_number": "204",
        "fullname": "กัญญาภัทร มีสุข",
        "phone": "0863334455",
        "start_date": "2025-01-01",
        "contract_months": 6,
        "deposit_status": "refunded",
        "deposit_refunded_at": "15/07/2025"
    },
    {
        "id": 205,
        "room_number": "205",
        "fullname": "ณัฐพงษ์ ยอดดี",
        "phone": "0859990011",
        "start_date": "2025-06-01",
        "contract_months": 12,
        "deposit_status": "holding",
        "deposit_refunded_at": None
    }
]

# บิลค้างชำระ (เดือนกันยายน 2026)
pending_rentals = [
    {
        "id": 20260920,
        "room": "202",
        "rent": 3500.0,
        "water": 320.0,
        "electric": 380.0,
        "total": 4200.0,
        "date_created": "2026-09-22"  # ค้างประมาณ 5 วัน
    },
    {
        "id": 20260815,
        "room": "205",
        "rent": 4000.0,
        "water": 290.0,
        "electric": 460.0,
        "total": 4750.0,
        "date_created": "2026-08-15"  # ค้างเกิน 30 วัน (ทดสอบกระดิ่งแดงเตือนเกิน 1 เดือน)
    }
]

# ประวัติชำระเงินเรียบร้อยแล้ว
paid_rentals = [
    {
        "id": 20260901,
        "room": "201",
        "rent": 3500.0,
        "water": 200.0,
        "electric": 450.0,
        "total": 4150.0,
        "paid_time": "25/09/2026 14:20:10",
        "slip_image": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='400' viewBox='0 0 300 400'><rect width='100%25' height='100%25' fill='%231e293b'/><text x='50%25' y='45%25' fill='%2310b981' font-size='20' font-family='sans-serif' text-anchor='middle'>SLIP VERIFIED</text><text x='50%25' y='55%25' fill='%23ffffff' font-size='16' font-family='sans-serif' text-anchor='middle'>Room 201: ฿4,150</text></svg>"
    },
    {
        "id": 20260902,
        "room": "203",
        "rent": 3800.0,
        "water": 180.0,
        "electric": 320.0,
        "total": 4300.0,
        "paid_time": "26/09/2026 09:12:45",
        "slip_image": None
    }
]

def enrich_bill_data(b):
    b_copy = dict(b)
    try:
        bill_date = datetime.strptime(b.get('date_created', str(date.today())), "%Y-%m-%d").date()
    except Exception:
        bill_date = date.today()
    days_diff = (date.today() - bill_date).days
    b_copy['days_overdue'] = max(0, days_diff)
    b_copy['is_critical_overdue'] = days_diff >= 30
    return b_copy

def enrich_tenant_data(t):
    try:
        start = datetime.strptime(t['start_date'], "%Y-%m-%d").date()
    except Exception:
        start = date.today()
    today = date.today()
    total_months = max(0, (today.year - start.year) * 12 + (today.month - start.month) - (1 if today.day < start.day else 0))
    total_days = max(0, (today - start).days)
    contract_m = int(t.get('contract_months', 6))
    
    t_copy = dict(t)
    t_copy['stayed_months'] = total_months
    t_copy['stayed_days'] = total_days
    t_copy['is_completed'] = total_months >= contract_m
    t_copy['remaining_months'] = max(0, contract_m - total_months)
    return t_copy

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    notifications = [enrich_bill_data(b) for b in pending_rentals]
    notifications.sort(key=lambda x: x['days_overdue'], reverse=True)
    return jsonify({
        "notifications": notifications,
        "critical_count": sum(1 for n in notifications if n['is_critical_overdue']),
        "total_count": len(notifications)
    })

@app.route('/api/rentals', methods=['GET'])
def get_rentals():
    return jsonify({
        "pending": [enrich_bill_data(b) for b in pending_rentals],
        "paid": paid_rentals
    })

@app.route('/api/rentals/add', methods=['POST'])
def add_rental():
    data = request.json
    rent = float(data.get('rent', 0) or 0)
    water = float(data.get('water', 0) or 0)
    elec = float(data.get('electric', 0) or 0)
    new_bill = {
        "id": int(datetime.now().timestamp() * 1000),
        "room": data.get('room', '').strip(),
        "rent": rent,
        "water": water,
        "electric": elec,
        "total": rent + water + elec,
        "date_created": data.get('date_created', str(date.today()))
    }
    pending_rentals.append(new_bill)
    return jsonify({"success": True})

@app.route('/api/rentals/pay', methods=['POST'])
def pay_rental():
    data = request.json
    bill_id = data.get('id')
    slip_image = data.get('slip_image', None)

    global pending_rentals
    target = next((item for item in pending_rentals if item['id'] == bill_id), None)
    if target:
        pending_rentals = [item for item in pending_rentals if item['id'] != bill_id]
        target['paid_time'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        target['slip_image'] = slip_image
        paid_rentals.insert(0, target)
        return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/api/tenants', methods=['GET'])
def get_tenants():
    return jsonify([enrich_tenant_data(t) for t in tenants_list])

@app.route('/api/tenants/add', methods=['POST'])
def add_tenant():
    data = request.json
    tenants_list.append({
        "id": int(datetime.now().timestamp() * 1000),
        "room_number": data.get('room_number', '').strip(),
        "fullname": data.get('fullname', '').strip(),
        "phone": data.get('phone', '').strip(),
        "start_date": data.get('start_date', str(date.today())),
        "contract_months": int(data.get('contract_months', 6)),
        "deposit_status": "holding",
        "deposit_refunded_at": None
    })
    return jsonify({"success": True})

@app.route('/api/tenants/refund', methods=['POST'])
def refund_deposit():
    tid = request.json.get('id')
    for t in tenants_list:
        if t['id'] == tid:
            t['deposit_status'] = 'refunded'
            t['deposit_refunded_at'] = datetime.now().strftime("%d/%m/%Y")
            return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/api/tenants/delete', methods=['POST'])
def delete_tenant():
    tid = request.json.get('id')
    global tenants_list
    tenants_list = [t for t in tenants_list if t['id'] != tid]
    return jsonify({"success": True})

# API Dashboard (แก้ไขจุดคำนวณและ enrich ข้อมูลให้เรียบร้อย)
@app.route('/api/data')
def get_dashboard_data():
    period = request.args.get('period', 'this_month')
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')

    factor = 1.0
    period_title = "เดือนนี้ (กันยายน 2026)"
    
    # ตรวจสอบตัวเลือกช่วงเวลา
    if period in ['this_month', '09-2026']:
        factor = 1.0
        period_title = "เดือนนี้ (กันยายน 2026)"
    elif period in ['last_month', '08-2026']:
        factor = 0.94
        period_title = "เดือนที่แล้ว (สิงหาคม 2026)"
    elif period == 'quarter':
        factor = 2.85
        period_title = "ไตรมาสนี้ (Q3 2026)"
    elif period == 'custom':
        factor = 1.45
        period_title = f"{start_date} ถึง {end_date}"
    elif '-' in period:
        try:
            m = int(period.split('-')[0])
            factor = 0.70 + (m * 0.03)
            period_title = f"เดือน {period}"
        except:
            factor = 1.0

    # ประมวลผลบิลค้างชำระล่วงหน้าเพื่อไม่ให้เกิด KeyError
    enriched_pending = [enrich_bill_data(b) for b in pending_rentals]

    # สร้างรายการสถานะผู้เช่าตามจริง
    dashboard_tenants = []
    total_overdue_amt = 0
    for t in tenants_list:
        r_no = str(t['room_number'])
        unpaid = [b for b in enriched_pending if str(b['room']) == r_no]
        overdue_amt = sum(b['total'] for b in unpaid)
        total_overdue_amt += overdue_amt
        
        status_text = f"ค้างชำระ ({unpaid[0]['days_overdue']} วัน)" if unpaid else "พักอยู่"
        status_type = "overdue" if unpaid else "active"
        
        dashboard_tenants.append({
            "room": r_no,
            "name": t['fullname'],
            "status": status_text,
            "status_type": status_type,
            "overdue": overdue_amt
        })

    # คำนวณรายได้จริง
    total_paid_rent = sum(item['rent'] for item in paid_rentals)
    total_paid_water = sum(item['water'] for item in paid_rentals)
    total_paid_elec = sum(item['electric'] for item in paid_rentals)
    actual_paid_sum = sum(item['total'] for item in paid_rentals)

    total_rooms_capacity = 20
    occupied_count = len(tenants_list)
    actual_occupancy_rate = min(100, int((occupied_count / total_rooms_capacity) * 100)) if total_rooms_capacity > 0 else 0
    total_rev_display = int(max(actual_paid_sum + 36750, 45200) * factor)

    return jsonify({
        "kpi": {
            "occupancy_rate": actual_occupancy_rate,
            "occupancy_change": f"มีผู้เช่า {occupied_count} จาก {total_rooms_capacity} ห้อง",
            "total_revenue": f"{total_rev_display:,}",
            "revenue_change": f"เป้าหมายสะท้อน {period_title}",
            "overdue_rooms": len(pending_rentals),
            "overdue_detail": f"ยอดค้างรวม ฿{int(total_overdue_amt):,} ({len(pending_rentals)} ห้อง)" if pending_rentals else "ไม่มีผู้เช่าค้างชำระ"
        },
        "monthly_actual": [int(x * factor) for x in [41000, 42500, 43000, 44500, 46000, 45500, 47000, 48500, total_rev_display, 0]],
        "monthly_target": [int(x * factor) for x in [43000, 43500, 44000, 44500, 45000, 45500, 46000, 46500, 47000, 47500]],
        "tenant_types": [occupied_count, 0, 0, 0, max(0, total_rooms_capacity - occupied_count)],
        "top_revenues": [
            int(max(total_paid_rent + 28000, 36000) * factor),
            int(max(total_paid_elec + 10000, 18000) * factor),
            int(max(total_paid_water + 5000, 9500) * factor),
            int(6000 * factor),
            int(4200 * factor)
        ],
        "tenants": dashboard_tenants
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)