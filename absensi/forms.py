"""
Form untuk Sistem Absensi RFID.
"""

from django import forms


class LoginForm(forms.Form):
    """Form login untuk guru dan admin."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True,
        }),
        label='Username'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        }),
        label='Password'
    )


class RekapFilterForm(forms.Form):
    """Form filter untuk rekap bulanan kehadiran."""
    kelas = forms.IntegerField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Kelas'
    )
    tanggal_mulai = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        }),
        label='Tanggal Mulai'
    )
    tanggal_selesai = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        }),
        label='Tanggal Selesai'
    )
