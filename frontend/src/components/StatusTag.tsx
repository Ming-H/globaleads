import { Tag } from 'antd';

const statusConfig: Record<
  string,
  { color: string; text: string }
> = {
  pending: { color: 'blue', text: '等待中' },
  running: { color: 'orange', text: '运行中' },
  completed: { color: 'green', text: '已完成' },
  failed: { color: 'red', text: '失败' },
  uncontacted: { color: 'default', text: '未联系' },
  contacted: { color: 'processing', text: '已联系' },
  replied: { color: 'success', text: '已回复' },
  invalid: { color: 'error', text: '无效' },
};

interface StatusTagProps {
  status: string;
}

export default function StatusTag({ status }: StatusTagProps) {
  const config = statusConfig[status] || { color: 'default', text: status };
  return <Tag color={config.color}>{config.text}</Tag>;
}
