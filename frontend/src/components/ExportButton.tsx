import { Button, Dropdown, message } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';

interface ExportButtonProps {
  onExport: (format: 'csv' | 'excel') => Promise<unknown>;
  loading?: boolean;
}

export default function ExportButton({ onExport, loading }: ExportButtonProps) {
  const handleExport = async (format: 'csv' | 'excel') => {
    try {
      const res = (await onExport(format)) as { data: Blob; headers: Record<string, string> };
      const blob = new Blob([res.data], {
        type: format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const contentDisposition = res.headers?.['content-disposition'];
      const fileName = contentDisposition
        ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
        : `export.${format === 'csv' ? 'csv' : 'xlsx'}`;
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch {
      message.error('导出失败，请重试');
    }
  };

  const items: MenuProps['items'] = [
    {
      key: 'csv',
      label: '导出 CSV',
      onClick: () => handleExport('csv'),
    },
    {
      key: 'excel',
      label: '导出 Excel',
      onClick: () => handleExport('excel'),
    },
  ];

  return (
    <Dropdown menu={{ items }} placement="bottomRight">
      <Button icon={<DownloadOutlined />} loading={loading}>
        导出
      </Button>
    </Dropdown>
  );
}
