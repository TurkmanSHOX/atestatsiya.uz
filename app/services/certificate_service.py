import os
import uuid
import random
from datetime import datetime, timedelta
import qrcode
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.extensions import db
from app.models.certificate import Certificate, CertificateStatus, CertificateVerification
from app.models.result import Result

class CertificateService:
    @staticmethod
    def generate_certificate(result_id: int):
        result = Result.query.get(result_id)
        if not result or not result.is_passed:
            return None

        # Agar allaqachon mavjud bo'lsa
        existing = Certificate.query.filter_by(result_id=result.id).first()
        if existing:
            return existing

        user = result.user
        attestation = result.attestation

        # Unikal raqam va UUID
        year = datetime.utcnow().year
        random_code = random.randint(100000, 999999)
        cert_number = f"AT-{year}-{random_code}"
        verif_uuid = str(uuid.uuid4())

        valid_months = attestation.certificate_validity_months or 36
        issue_date = datetime.utcnow().date()
        valid_until = issue_date + timedelta(days=valid_months * 30)

        # Upload papkalarini aniqlash
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        qr_dir = os.path.join(base_dir, 'static', 'uploads', 'qr')
        pdf_dir = os.path.join(base_dir, 'static', 'uploads', 'certificates')
        os.makedirs(qr_dir, exist_ok=True)
        os.makedirs(pdf_dir, exist_ok=True)

        # 1. QR kod generatsiyasi
        # Saytning ochiq verifikatsiya URL manzili
        qr_filename = f"qr_{verif_uuid}.png"
        qr_file_path = os.path.join(qr_dir, qr_filename)
        verification_url = f"/verify-certificate/{verif_uuid}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=6,
            border=2,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0d5c3a", back_color="white")
        img.save(qr_file_path)

        # 2. PDF generatsiyasi (Landscape rasmiy sertifikat)
        pdf_filename = f"cert_{cert_number}.pdf"
        pdf_file_path = os.path.join(pdf_dir, pdf_filename)

        doc = SimpleDocTemplate(
            pdf_file_path,
            pagesize=landscape(letter),
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CertTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=26,
            leading=30,
            alignment=1, # Center
            textColor=colors.HexColor('#0d5c3a')
        )

        subtitle_style = ParagraphStyle(
            'CertSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=13,
            leading=16,
            alignment=1,
            textColor=colors.HexColor('#333333')
        )

        name_style = ParagraphStyle(
            'CertName',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            alignment=1,
            textColor=colors.HexColor('#1b4332')
        )

        body_style = ParagraphStyle(
            'CertBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=12,
            leading=16,
            alignment=1,
            textColor=colors.HexColor('#444444')
        )

        meta_style = ParagraphStyle(
            'CertMeta',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            alignment=0,
            textColor=colors.HexColor('#555555')
        )

        elements = []

        elements.append(Paragraph("O'ZBEKISTON RESPUBLIKASI", subtitle_style))
        elements.append(Paragraph("MILLIY PROFESSIONAL ATTESTATSIYA VA IMTIHON TIZIMI", subtitle_style))
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("MALAKA SERTIFIKATI", title_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"№ {cert_number}", subtitle_style))
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("Ushbu sertifikat tasdiqlaydiki,", body_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(user.full_name.upper(), name_style))
        elements.append(Spacer(1, 12))

        elements.append(Paragraph(
            f"<b>«{attestation.title}»</b> bo'yicha professional attestatsiya sinovlaridan muvaffaqiyatli o'tdi va <b>{result.percentage}%</b> natija ko'rsatdi.",
            body_style
        ))
        elements.append(Spacer(1, 30))

        # Bottom section: QR code + Dates + Signatures
        qr_img = RLImage(qr_file_path, width=1.1*inch, height=1.1*inch)
        
        info_text = Paragraph(
            f"<b>Berilgan sana:</b> {issue_date.strftime('%d.%m.%Y')}<br/>"
            f"<b>Amal qilish muddati:</b> {valid_until.strftime('%d.%m.%Y')} gacha<br/>"
            f"<b>Holati:</b> HAQIQIY (ACTIVE)<br/>"
            f"<b>QR verifikatsiya:</b> attestatsiya.uz/verify-certificate/{verif_uuid}",
            meta_style
        )

        stamp_text = Paragraph(
            "<b>Davlat Attestatsiya Markazi</b><br/>"
            "Elektron Raqamli Imzo: TASDIQLANGAN<br/>"
            "Boshqaruv Kengashi Raisi<br/>"
            "<i>(Elektron sertifikat qog'oz nusxasi bilan teng yuridik kuchga ega)</i>",
            meta_style
        )

        table_data = [[qr_img, info_text, stamp_text]]
        t = Table(table_data, colWidths=[1.3*inch, 3.8*inch, 3.8*inch])
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
        ]))

        elements.append(t)
        doc.build(elements)

        # Bazaga saqlash
        cert = Certificate(
            certificate_number=cert_number,
            verification_uuid=verif_uuid,
            user_id=user.id,
            attestation_id=attestation.id,
            result_id=result.id,
            issue_date=issue_date,
            valid_until=valid_until,
            status=CertificateStatus.ACTIVE,
            pdf_path=f"uploads/certificates/{pdf_filename}",
            qr_code_path=f"uploads/qr/{qr_filename}"
        )
        db.session.add(cert)
        db.session.commit()
        return cert

    @staticmethod
    def verify(cert_number_or_uuid: str, ip_address: str = None, user_agent: str = None):
        """
        Ochiq QR verifikatsiya tekshiruvi.
        """
        cert = Certificate.query.filter(
            (Certificate.verification_uuid == cert_number_or_uuid) |
            (Certificate.certificate_number == cert_number_or_uuid)
        ).first()

        if not cert:
            return {'found': False, 'message': "Bunday raqamli sertifikat tizimda ro'yxatga olinmagan."}

        # Log verifikatsiya
        try:
            verif = CertificateVerification(
                certificate_id=cert.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(verif)
            db.session.commit()
        except Exception:
            pass

        return {
            'found': True,
            'certificate': cert.to_dict(),
            'is_valid': cert.is_valid,
            'status': cert.status
        }
